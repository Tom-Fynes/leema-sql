import pytest
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
