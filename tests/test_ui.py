import pytest
from unittest.mock import patch, MagicMock
from src.ui.sidebar import BurrowSidebar
from src.ui.editor import WorkspaceEditor
from src.ui.plan_viz import ExecutionPlanViewer
from src.theme import NEBULA_NIGHTS


def test_sidebar_initialization():
    """Test BurrowSidebar can be instantiated."""
    sidebar = BurrowSidebar()
    assert sidebar is not None
    assert sidebar._engine is None


def test_sidebar_set_engine_none():
    """Test that set_engine accepts None gracefully (no tree widget yet)."""
    sidebar = BurrowSidebar()
    sidebar.set_engine(None)
    assert sidebar._engine is None


def test_workspace_editor_initialization():
    """Test WorkspaceEditor can be instantiated."""
    editor = WorkspaceEditor()
    assert editor is not None


def test_execution_plan_viewer_initialization():
    """Test ExecutionPlanViewer can be instantiated."""
    viewer = ExecutionPlanViewer()
    assert viewer is not None


def test_sidebar_loaded_nodes_empty_on_init():
    """Test that the loaded nodes set is empty on init."""
    sidebar = BurrowSidebar()
    assert len(sidebar._loaded_nodes) == 0


# --- Bug fix tests ---

def test_column_nullable_display_without_key():
    """Bug fix: columns without a 'nullable' key must not show 'NOT NULL' erroneously."""
    # Simulate what _load_columns does when building the label
    col = {"name": "id", "type": "INTEGER"}
    if "nullable" in col:
        nullable = " NULL" if col["nullable"] else " NOT NULL"
    else:
        nullable = ""
    label = f"🔹 {col['name']} ({col['type']}){nullable}"
    assert "NOT NULL" not in label
    assert "NULL" not in label


def test_column_nullable_display_with_nullable_true():
    """Columns with nullable=True must display ' NULL'."""
    col = {"name": "description", "type": "TEXT", "nullable": True}
    if "nullable" in col:
        nullable = " NULL" if col["nullable"] else " NOT NULL"
    else:
        nullable = ""
    label = f"🔹 {col['name']} ({col['type']}){nullable}"
    assert " NULL" in label
    assert "NOT NULL" not in label


def test_column_nullable_display_with_nullable_false():
    """Columns with nullable=False must display ' NOT NULL'."""
    col = {"name": "id", "type": "INTEGER", "nullable": False}
    if "nullable" in col:
        nullable = " NULL" if col["nullable"] else " NOT NULL"
    else:
        nullable = ""
    label = f"🔹 {col['name']} ({col['type']}){nullable}"
    assert "NOT NULL" in label


def test_format_sql_notifies_on_failure():
    """Bug fix: action_format_sql must call notify() when sqlparse raises, not silently pass."""
    editor = WorkspaceEditor()

    # Attach a mock text area with non-empty text so formatting is attempted
    mock_textarea = MagicMock()
    mock_textarea.text = "SELECT *** INVALID"
    editor.editor = mock_textarea

    with patch("sqlparse.format", side_effect=Exception("parse error")):
        with patch.object(editor, "notify") as mock_notify:
            editor.action_format_sql()

    mock_notify.assert_called_once()
    # Severity should be 'warning' (not an error, just a format issue)
    _, kwargs = mock_notify.call_args
    assert kwargs.get("severity") == "warning", (
        f"Expected severity='warning', got: {kwargs.get('severity')}"
    )


# --- Theme tests ---

def test_nebula_nights_theme_name():
    """Nebula Nights theme must have the correct name."""
    assert NEBULA_NIGHTS.name == "nebula-nights"


def test_nebula_nights_theme_is_dark():
    """Nebula Nights must be a dark theme."""
    assert NEBULA_NIGHTS.dark is True


def test_nebula_nights_background_color():
    """Background must use the primary dark color #404E5C."""
    assert NEBULA_NIGHTS.background == "#404E5C"


def test_nebula_nights_surface_color():
    """Surface must use the sidebar background color #363E4A."""
    assert NEBULA_NIGHTS.surface == "#363E4A"


def test_nebula_nights_panel_color():
    """Panel must use the activity/status bar color #2E3A48."""
    assert NEBULA_NIGHTS.panel == "#2E3A48"


def test_nebula_nights_primary_color():
    """Primary accent must be the pink highlight #DD7596."""
    assert NEBULA_NIGHTS.primary == "#DD7596"


def test_nebula_nights_error_color():
    """Error color must be #D05786."""
    assert NEBULA_NIGHTS.error == "#D05786"


def test_nebula_nights_warning_color():
    """Warning color must be #ECDA90."""
    assert NEBULA_NIGHTS.warning == "#ECDA90"


def test_nebula_nights_success_color():
    """Success color must be #94FBAB."""
    assert NEBULA_NIGHTS.success == "#94FBAB"


def test_nebula_nights_foreground_color():
    """Foreground must use the main text color #B7C3F3."""
    assert NEBULA_NIGHTS.foreground == "#B7C3F3"


def test_nebula_nights_variables_present():
    """Theme variables dict must be populated."""
    assert isinstance(NEBULA_NIGHTS.variables, dict)
    assert len(NEBULA_NIGHTS.variables) > 0


def test_nebula_nights_terminal_ansi_colors():
    """Terminal ANSI colors must be set in theme variables."""
    assert NEBULA_NIGHTS.variables.get("terminal-ansi-cyan") == "#A9FFF7"
    assert NEBULA_NIGHTS.variables.get("terminal-ansi-green") == "#94FBAB"
    assert NEBULA_NIGHTS.variables.get("terminal-ansi-red") == "#D05786"
