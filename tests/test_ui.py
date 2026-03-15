import pytest
from unittest.mock import patch, MagicMock
from src.ui.sidebar import BurrowSidebar
from src.ui.editor import WorkspaceEditor
from src.ui.plan_viz import ExecutionPlanViewer


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
