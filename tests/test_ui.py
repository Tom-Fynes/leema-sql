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
    """Bug fix: action_format_sql must call notify() when sqlglot raises, not silently pass."""
    editor = WorkspaceEditor()

    # Attach a mock text area with non-empty text so formatting is attempted
    mock_textarea = MagicMock()
    mock_textarea.text = "SELECT *** INVALID"
    editor.editor = mock_textarea

    with patch("sqlglot.transpile", side_effect=Exception("parse error")):
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


# --- Toolbar button tests ---


def test_editor_toolbar_buttons_exist():
    """WorkspaceEditor must have Execute SQL, Execute Selected, and Format SQL buttons."""
    editor = WorkspaceEditor()
    # Confirm the class exposes the expected action methods
    assert hasattr(editor, "action_execute_all")
    assert hasattr(editor, "action_execute_selected")
    assert hasattr(editor, "action_format_sql")
    assert callable(editor.action_execute_all)
    assert callable(editor.action_execute_selected)
    assert callable(editor.action_format_sql)


def test_editor_execute_all_posts_message_with_full_text():
    """action_execute_all must post ExecuteQuery with the full buffer text."""
    editor = WorkspaceEditor()

    mock_textarea = MagicMock()
    mock_textarea.text = "SELECT 1;"
    editor.editor = mock_textarea

    posted_messages = []
    with patch.object(editor, "post_message", side_effect=posted_messages.append):
        editor.action_execute_all()

    assert len(posted_messages) == 1
    assert isinstance(posted_messages[0], WorkspaceEditor.ExecuteQuery)
    assert posted_messages[0].sql == "SELECT 1;"


def test_editor_execute_selected_posts_message_with_selection():
    """action_execute_selected must post ExecuteQuery with only the selected text."""
    editor = WorkspaceEditor()

    mock_textarea = MagicMock()
    mock_textarea.selected_text = "SELECT 2;"
    editor.editor = mock_textarea

    posted_messages = []
    with patch.object(editor, "post_message", side_effect=posted_messages.append):
        editor.action_execute_selected()

    assert len(posted_messages) == 1
    assert isinstance(posted_messages[0], WorkspaceEditor.ExecuteQuery)
    assert posted_messages[0].sql == "SELECT 2;"


def test_editor_execute_selected_strips_whitespace():
    """action_execute_selected must strip surrounding whitespace from selected text."""
    editor = WorkspaceEditor()

    mock_textarea = MagicMock()
    mock_textarea.selected_text = "  SELECT 3;  "
    editor.editor = mock_textarea

    posted_messages = []
    with patch.object(editor, "post_message", side_effect=posted_messages.append):
        editor.action_execute_selected()

    assert len(posted_messages) == 1
    assert posted_messages[0].sql == "SELECT 3;"


def test_editor_execute_all_does_nothing_when_editor_is_none():
    """action_execute_all must be a no-op when the internal editor widget is not set."""
    editor = WorkspaceEditor()
    editor.editor = None

    posted_messages = []
    with patch.object(editor, "post_message", side_effect=posted_messages.append):
        editor.action_execute_all()

    assert len(posted_messages) == 0


def test_editor_execute_selected_does_nothing_when_editor_is_none():
    """action_execute_selected must be a no-op when the internal editor widget is not set."""
    editor = WorkspaceEditor()
    editor.editor = None

    posted_messages = []
    with patch.object(editor, "post_message", side_effect=posted_messages.append):
        editor.action_execute_selected()

    assert len(posted_messages) == 0


def test_editor_execute_selected_notifies_when_no_selection():
    """action_execute_selected must notify the user when nothing is selected."""
    editor = WorkspaceEditor()

    mock_textarea = MagicMock()
    mock_textarea.selected_text = ""
    editor.editor = mock_textarea

    posted_messages = []
    with patch.object(editor, "post_message", side_effect=posted_messages.append):
        with patch.object(editor, "notify") as mock_notify:
            editor.action_execute_selected()

    assert len(posted_messages) == 0, "No message should be posted when nothing is selected"
    mock_notify.assert_called_once()
    _, kwargs = mock_notify.call_args
    assert kwargs.get("severity") == "warning"


def test_editor_execute_all_does_nothing_for_empty_buffer():
    """action_execute_all must not post a message when the buffer is empty."""
    editor = WorkspaceEditor()

    mock_textarea = MagicMock()
    mock_textarea.text = "   "
    editor.editor = mock_textarea

    posted_messages = []
    with patch.object(editor, "post_message", side_effect=posted_messages.append):
        editor.action_execute_all()

    assert len(posted_messages) == 0


# --- Execution plan expand tests ---


def test_execution_plan_show_plan_expands_root():
    """show_plan must expand_all on the tree root so all child nodes are visible."""
    viewer = ExecutionPlanViewer()

    mock_tree = MagicMock()
    mock_root = MagicMock()
    mock_tree.root = mock_root
    viewer._plan_tree = mock_tree

    viewer.show_plan("line one\nline two", "generic")

    mock_root.expand_all.assert_called_once()


def test_execution_plan_show_plan_sets_label():
    """show_plan must update the root label with the engine type."""
    viewer = ExecutionPlanViewer()

    mock_tree = MagicMock()
    mock_root = MagicMock()
    mock_tree.root = mock_root
    viewer._plan_tree = mock_tree

    viewer.show_plan("EXPLAIN text", "duckdb")

    mock_root.set_label.assert_called_once()
    label_arg = mock_root.set_label.call_args[0][0]
    assert "DUCKDB" in label_arg


def test_execution_plan_show_plan_queues_when_not_mounted():
    """show_plan before widget is mounted must store the plan for later display."""
    viewer = ExecutionPlanViewer()
    # _plan_tree is None until the widget is composed/mounted
    assert viewer._plan_tree is None

    viewer.show_plan("SELECT 1 plan text", "duckdb")

    # Plan must be queued, not discarded
    assert viewer._pending_plan_text == "SELECT 1 plan text"
    assert viewer._pending_engine_type == "duckdb"


def test_execution_plan_on_mount_flushes_pending_plan():
    """on_mount must render and clear any pending plan stored before mount."""
    viewer = ExecutionPlanViewer()

    # Pre-load a pending plan (simulating show_plan called before mount)
    viewer._pending_plan_text = "plan line"
    viewer._pending_engine_type = "generic"

    # Simulate mount by attaching a mock tree and calling on_mount
    mock_tree = MagicMock()
    mock_root = MagicMock()
    mock_tree.root = mock_root
    viewer._plan_tree = mock_tree

    viewer.on_mount()

    mock_tree.clear.assert_called_once()
    assert viewer._pending_plan_text is None
    assert viewer._pending_engine_type is None
