"""The Workspace - SQL editor with syntax highlighting and formatting."""
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import TextArea
from textual.message import Message
from textual.binding import Binding
import sqlparse
from pygments.lexers import SqlLexer
from pygments.token import Token


class WorkspaceEditor(VerticalScroll):
    """SQL editor with syntax highlighting and formatting."""

    DEFAULT_CSS = """
    WorkspaceEditor {
        border: solid $primary;
        background: $surface;
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
        self.editor = TextArea(
            language="sql",
            theme="monokai",
            id="sql-editor"
        )
        self.editor.show_line_numbers = True
        yield self.editor

    def action_execute_query(self) -> None:
        """Execute the selected text or entire buffer."""
        if not self.editor:
            return

        # Get selected text or full text
        selected = self.editor.selected_text
        sql = selected if selected else self.editor.text

        if sql.strip():
            self.post_message(self.ExecuteQuery(sql))

    def action_format_sql(self) -> None:
        """Format SQL using sqlparse."""
        if not self.editor:
            return

        current_text = self.editor.text
        if not current_text.strip():
            return

        try:
            formatted = sqlparse.format(
                current_text,
                reindent=True,
                keyword_case="upper",
                identifier_case="lower",
                strip_comments=False,
                use_space_around_operators=True
            )
            self.editor.text = formatted
        except Exception:
            # Silently fail formatting - don't break user flow
            pass

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
        self.editor.delete_line(cursor_location[0])
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
