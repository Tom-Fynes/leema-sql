"""The Results Console - DataTable for query results with copy/paste support."""
from typing import Any, List, Optional
from textual.app import ComposeResult
from textual.containers import VerticalScroll, Vertical
from textual.widgets import DataTable, Static, Label
from textual.binding import Binding
import csv
from io import StringIO


class ResultsConsole(Vertical):
    """Query results display with copy/paste support."""

    DEFAULT_CSS = """
    ResultsConsole {
        border: solid $primary;
        background: $surface;
    }
    
    ResultsConsole DataTable {
        width: 1fr;
        height: 1fr;
    }
    
    ResultsConsole #results-header {
        height: 3;
        background: $boost;
        padding: 1;
    }
    
    ResultsConsole #results-status {
        dock: bottom;
        height: 1;
        background: $panel;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "copy_selection", "Copy", show=True),
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.table: Optional[DataTable] = None
        self.header_widget: Optional[Static] = None
        self.status_widget: Optional[Label] = None
        self._current_data: List[List[Any]] = []

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        self.header_widget = Static("📊 Results", id="results-header")
        yield self.header_widget

        self.table = DataTable(id="results-table", zebra_stripes=True)
        self.table.cursor_type = "row"
        yield self.table

        self.status_widget = Label("Ready", id="results-status")
        yield self.status_widget

    def show_results(self, columns: List[str], rows: List[tuple]) -> None:
        """Display query results."""
        if not self.table:
            return

        # Clear existing data
        self.table.clear(columns=True)
        self._current_data = []

        if not columns or not rows:
            self.update_status("No results")
            return

        # Add columns
        for col in columns:
            self.table.add_column(col, key=col)

        # Add rows
        for row in rows:
            # Convert row to list and store
            row_data = list(row)
            self._current_data.append(row_data)
            self.table.add_row(*row_data)

        # Update status
        self.update_status(f"{len(rows)} rows returned")

    def show_error(self, error: str) -> None:
        """Display error message."""
        if self.table:
            self.table.clear(columns=True)
            self._current_data = []
        self.update_status(f"❌ Error: {error}")

    def update_status(self, message: str) -> None:
        """Update status bar."""
        if self.status_widget:
            self.status_widget.update(message)

    def update_header(self, text: str) -> None:
        """Update header text."""
        if self.header_widget:
            self.header_widget.update(text)

    def action_copy_selection(self) -> None:
        """Copy selected rows to clipboard as CSV."""
        if not self.table or not self._current_data:
            return

        try:
            # Get selected row indices
            cursor_row = self.table.cursor_row

            if cursor_row < 0 or cursor_row >= len(self._current_data):
                return

            # Get column names
            columns = [col.label.plain for col in self.table.columns.values()]

            # Get selected row data
            selected_data = self._current_data[cursor_row]

            # Format as CSV
            output = StringIO()
            # TSV for better paste support
            writer = csv.writer(output, delimiter='\t')
            writer.writerow(columns)
            writer.writerow(selected_data)

            csv_text = output.getvalue()

            # Copy to system clipboard
            self._copy_to_clipboard(csv_text)
            self.update_status(f"✓ Copied row {cursor_row + 1}")

        except Exception as e:
            self.update_status(f"Copy failed: {str(e)}")

    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to system clipboard."""
        try:
            # Try using pyperclip if available
            import pyperclip
            pyperclip.copy(text)
        except ImportError:
            # Fallback: write to xclip on Linux
            try:
                import subprocess
                process = subprocess.Popen(
                    ['xclip', '-selection', 'clipboard'],
                    stdin=subprocess.PIPE,
                    close_fds=True
                )
                process.communicate(input=text.encode('utf-8'))
            except Exception:
                # Last resort: just log it
                self.app.log(f"Could not copy to clipboard: {text}")
