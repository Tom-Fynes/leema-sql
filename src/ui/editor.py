"""The Workspace - SQL editor with syntax highlighting and formatting."""

from typing import Optional
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import TextArea, Button
from textual.message import Message
from textual.binding import Binding
import sqlglot


class WorkspaceEditor(Vertical):
    """SQL editor with syntax highlighting and formatting."""

    DEFAULT_CSS = """
    WorkspaceEditor {
        border: solid $primary;
        background: $surface;
    }

    WorkspaceEditor #editor-toolbar {
        height: 3;
        background: $panel;
        padding: 0 1;
        align: left middle;
    }

    WorkspaceEditor #editor-toolbar Button {
        margin: 0 1 0 0;
        min-width: 16;
        height: 3;
        background: $boost;
        color: $foreground;
        border: none;
    }

    WorkspaceEditor #editor-toolbar Button:hover {
        background: $accent;
        color: $background;
    }

    WorkspaceEditor TextArea {
        width: 1fr;
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("ctrl+enter", "execute_query", "Execute Query", show=True),
        Binding("shift+f", "format_sql", "Format SQL", show=True),
        Binding("ctrl+/", "toggle_comment", "Toggle Comment", show=False),
    ]

    class ExecuteQuery(Message):
        """Posted when user wants to execute SQL."""

        def __init__(self, sql: str) -> None:
            self.sql = sql
            super().__init__()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.editor: Optional[TextArea] = None

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Horizontal(id="editor-toolbar"):
            yield Button("▶ Execute SQL", id="btn-execute-all")
            yield Button("▶ Execute Selected", id="btn-execute-sel")
            yield Button("✦ Format SQL", id="btn-format-sql")
        self.editor = TextArea(language="sql", theme="monokai", id="sql-editor")
        self.editor.show_line_numbers = True
        yield self.editor

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle toolbar button presses."""
        if event.button.id == "btn-execute-all":
            self.action_execute_all()
        elif event.button.id == "btn-execute-sel":
            self.action_execute_selected()
        elif event.button.id == "btn-format-sql":
            self.action_format_sql()

    def action_execute_query(self) -> None:
        """Execute the selected text or entire buffer (keyboard shortcut)."""
        if not self.editor:
            return

        # Get selected text or full text
        selected = self.editor.selected_text
        sql = selected if selected else self.editor.text

        if sql.strip():
            self.post_message(self.ExecuteQuery(sql))

    def action_execute_all(self) -> None:
        """Execute the entire buffer."""
        if not self.editor:
            return

        sql = self.editor.text
        if sql.strip():
            self.post_message(self.ExecuteQuery(sql))

    def action_execute_selected(self) -> None:
        """Execute selected text only."""
        if not self.editor:
            return

        selected = self.editor.selected_text
        selected_stripped = selected.strip() if selected else ""
        if selected_stripped:
            self.post_message(self.ExecuteQuery(selected_stripped))
        else:
            self.notify("No text selected", severity="warning")

    def action_format_sql(self) -> None:
        """Format SQL using sqlglot."""
        if not self.editor:
            return

        current_text = self.editor.text
        if not current_text.strip():
            return

        try:
            statements = sqlglot.transpile(current_text, pretty=True)
            formatted = "\n\n".join(statements)
            self.editor.text = formatted
        except Exception:
            self.notify("Could not format SQL", severity="warning")

    def action_toggle_comment(self) -> None:
        """Toggle SQL comment on current line or selection."""
        if not self.editor:
            return

        # Basic implementation - toggle -- comment
        cursor_location = self.editor.cursor_location
        current_line = self.editor.get_line(cursor_location[0])

        if current_line.strip().startswith("--"):
            # Remove comment
            new_line = current_line.replace("--", "", 1)
        else:
            # Add comment
            new_line = f"-- {current_line}"

        # Replace line (this is simplified - actual implementation needs cursor management)
        self.editor.action_delete_line()
        self.editor.insert(new_line, cursor_location)

    def insert_text(self, text: str) -> None:
        """Insert text at current cursor position."""
        if self.editor:
            self.editor.insert(text)

    def get_text(self) -> str:
        """Get current editor content."""
        return self.editor.text if self.editor else ""

    def set_text(self, text: str) -> None:
        """Set editor content."""
        if self.editor:
            self.editor.text = text
