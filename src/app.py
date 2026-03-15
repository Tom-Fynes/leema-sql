"""Main Leema SQL IDE application."""
from typing import Optional
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, TabbedContent, TabPane, LoadingIndicator
from textual.worker import Worker, WorkerState

from .ui.sidebar import BurrowSidebar
from .ui.editor import WorkspaceEditor
from .ui.results import ResultsConsole
from .ui.plan_viz import ExecutionPlanViewer
from .config import LeemaConfig, ConnectionProfile
from .security import SecurityManager
from .drivers import get_engine
from .theme import NEBULA_NIGHTS


class LeemaApp(App):
    """Leema SQL IDE - Multi-engine TUI SQL client."""

    CSS = """
    Screen {
        background: $surface;
    }
    
    #main-container {
        width: 1fr;
        height: 1fr;
    }
    
    #left-pane {
        width: 30%;
        min-width: 20;
    }
    
    #right-pane {
        width: 70%;
    }
    
    #editor-pane {
        height: 50%;
    }
    
    #results-pane {
        height: 50%;
    }
    
    LoadingIndicator {
        dock: bottom;
        height: 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+o", "open_connection", "Connect", show=True),
        Binding("ctrl+e", "toggle_explain", "Explain", show=True),
        Binding("f5", "refresh_schema", "Refresh", show=True),
    ]

    TITLE = "Leema SQL IDE"
    SUB_TITLE = "Multi-Engine SQL Development Environment"

    def __init__(self, config_path: Optional[str] = None):
        super().__init__()
        self.config = LeemaConfig.load(config_path)
        self.security = SecurityManager()

        # State
        self._current_engine = None
        self._current_profile: Optional[ConnectionProfile] = None
        self._explain_mode = False

        # UI Components (will be set in compose)
        self.sidebar: Optional[BurrowSidebar] = None
        self.editor: Optional[WorkspaceEditor] = None
        self.results: Optional[ResultsConsole] = None
        self.plan_viewer: Optional[ExecutionPlanViewer] = None
        self.loading_indicator: Optional[LoadingIndicator] = None

    def compose(self) -> ComposeResult:
        """Create the application layout."""
        yield Header()

        with Container(id="main-container"):
            with Horizontal():
                # Left Pane: The Burrow (Sidebar)
                with Vertical(id="left-pane"):
                    self.sidebar = BurrowSidebar()
                    yield self.sidebar

                # Right Pane: Editor + Results
                with Vertical(id="right-pane"):
                    # Top: The Workspace (Editor)
                    with Container(id="editor-pane"):
                        self.editor = WorkspaceEditor()
                        yield self.editor

                    # Bottom: Tabbed Results/Plan Viewer
                    with Container(id="results-pane"):
                        with TabbedContent(initial="results-tab"):
                            with TabPane("Results", id="results-tab"):
                                self.results = ResultsConsole()
                                yield self.results

                            with TabPane("Execution Plan", id="plan-tab"):
                                self.plan_viewer = ExecutionPlanViewer()
                                yield self.plan_viewer

        # Global loading indicator
        self.loading_indicator = LoadingIndicator()
        yield self.loading_indicator

        yield Footer()

    def on_mount(self) -> None:
        """Handle app mount - register theme and auto-connect if default profile exists."""
        self.register_theme(NEBULA_NIGHTS)
        self.theme = NEBULA_NIGHTS.name
        if self.config.default_profile:
            self.connect_to_profile(self.config.default_profile)

    # ===== Connection Management =====

    def action_open_connection(self) -> None:
        """Open connection dialog (future: implement modal)."""
        # For now, connect to default or first available profile
        if self.config.profiles:
            profile_name = self.config.default_profile or list(
                self.config.profiles.keys())[0]
            self.connect_to_profile(profile_name)

    @work(exclusive=True, thread=True)
    async def connect_to_profile(self, profile_name: str) -> None:
        """Connect to a database profile."""
        if profile_name not in self.config.profiles:
            self.notify(
                f"Profile '{profile_name}' not found", severity="error")
            return

        profile = self.config.profiles[profile_name]
        self._current_profile = profile

        try:
            self.call_from_thread(self._show_loading)
            self.notify(f"Connecting to {profile.name}...")

            # Get password from vault if not in profile
            password = profile.password
            if not password and profile.username:
                password = self.security.get_password(
                    profile.engine,
                    profile.host,
                    profile.username
                )

            # Get engine class
            engine_class = get_engine(profile.engine)

            # Create engine instance
            self._current_engine = engine_class(
                host=profile.host,
                port=profile.port,
                database=profile.database,
                username=profile.username,
                password=password,
                ssl=profile.ssl,
                **profile.options
            )

            # Connect
            await self._current_engine.connect()

            # Update UI
            self.call_from_thread(self._on_connection_success, profile)

        except Exception as e:
            self.call_from_thread(self._on_connection_error, str(e))
        finally:
            self.call_from_thread(self._hide_loading)

    def _on_connection_success(self, profile: ConnectionProfile) -> None:
        """Handle successful connection."""
        self.notify(f"✓ Connected to {profile.name}", severity="information")
        self.sub_title = f"Connected: {profile.name} ({profile.engine})"

        # Update sidebar with new engine
        if self.sidebar:
            self.sidebar.set_engine(self._current_engine)

    def _on_connection_error(self, error: str) -> None:
        """Handle connection error."""
        self.notify(f"Connection failed: {error}", severity="error")
        self._current_engine = None

    def _show_loading(self) -> None:
        """Show loading indicator."""
        if self.loading_indicator:
            self.loading_indicator.display = True

    def _hide_loading(self) -> None:
        """Hide loading indicator."""
        if self.loading_indicator:
            self.loading_indicator.display = False

    # ===== Query Execution =====

    def on_workspace_editor_execute_query(self, message: WorkspaceEditor.ExecuteQuery) -> None:
        """Handle query execution request from editor."""
        if not self._current_engine:
            self.notify("Not connected to any database", severity="error")
            return

        sql = message.sql.strip()
        if not sql:
            return

        # Check if EXPLAIN mode
        if self._explain_mode:
            self.execute_explain(sql)
        else:
            self.execute_query(sql)

    @work(exclusive=True, thread=True)
    async def execute_query(self, sql: str) -> None:
        """Execute SQL query asynchronously."""
        try:
            self.call_from_thread(self._show_loading)
            self.call_from_thread(
                self._update_results_status, "Executing query...")

            # Execute query
            result = await self._current_engine.execute(sql)

            # Update UI with results
            self.call_from_thread(
                self._show_query_results,
                result.columns,
                result.rows,
                result.row_count,
                result.execution_time
            )

        except Exception as e:
            self.call_from_thread(self._show_query_error, str(e))
        finally:
            self.call_from_thread(self._hide_loading)

    @work(exclusive=True, thread=True)
    async def execute_explain(self, sql: str) -> None:
        """Execute EXPLAIN for query."""
        try:
            self.call_from_thread(self._show_loading)
            self.call_from_thread(
                self._update_results_status, "Generating execution plan...")

            # Get execution plan
            plan_text = await self._current_engine.get_explain_plan(sql)

            # Show plan in viewer
            self.call_from_thread(
                self._show_execution_plan,
                plan_text,
                self._current_profile.engine if self._current_profile else "unknown"
            )

            # Switch to plan tab
            self.call_from_thread(self._switch_to_plan_tab)

        except Exception as e:
            self.call_from_thread(self._show_query_error, str(e))
        finally:
            self.call_from_thread(self._hide_loading)

    def _show_query_results(self, columns: list, rows: list, row_count: int, exec_time: float) -> None:
        """Update results console with query data."""
        if self.results:
            self.results.show_results(columns, rows)
            self.results.update_header(
                f"📊 Results - {row_count} rows in {exec_time:.2f}s"
            )

    def _show_query_error(self, error: str) -> None:
        """Display query error."""
        if self.results:
            self.results.show_error(error)
        self.notify(f"Query error: {error}", severity="error")

    def _show_execution_plan(self, plan_text: str, engine_type: str) -> None:
        """Display execution plan."""
        if self.plan_viewer:
            self.plan_viewer.show_plan(plan_text, engine_type)

    def _switch_to_plan_tab(self) -> None:
        """Switch to execution plan tab."""
        tabbed = self.query_one(TabbedContent)
        tabbed.active = "plan-tab"

    def _update_results_status(self, message: str) -> None:
        """Update results status bar."""
        if self.results:
            self.results.update_status(message)

    # ===== Schema Navigation =====

    def on_burrow_sidebar_schema_selected(self, message: BurrowSidebar.SchemaSelected) -> None:
        """Handle schema item selection in sidebar."""
        node_type = message.node_type
        metadata = message.metadata

        if node_type == "table":
            # Insert SELECT statement template
            table_name = ".".join(message.path)
            sql = f"SELECT * FROM {table_name} LIMIT 100;"
            if self.editor:
                self.editor.insert_text(sql)

    def action_refresh_schema(self) -> None:
        """Refresh schema tree."""
        if self.sidebar and self._current_engine:
            self.sidebar.set_engine(self._current_engine)
            self.notify("Schema refreshed", severity="information")

    # ===== Explain Mode Toggle =====

    def action_toggle_explain(self) -> None:
        """Toggle EXPLAIN mode."""
        self._explain_mode = not self._explain_mode
        mode_text = "ON" if self._explain_mode else "OFF"
        self.notify(f"EXPLAIN mode: {mode_text}", severity="information")

    # ===== App Actions =====

    def action_quit(self) -> None:
        """Quit the application."""
        if self._current_engine:
            # Disconnect gracefully using the async close method
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._current_engine.close())
                else:
                    loop.run_until_complete(self._current_engine.close())
            except Exception:
                pass
        self.exit()


def run(config_path: Optional[str] = None) -> None:
    """Run the Leema SQL IDE application."""
    app = LeemaApp(config_path=config_path)
    app.run()
