import pytest
from leema.ui.sidebar import Sidebar
from leema.ui.editor import SQLTextEditor
from leema.ui.plan_viz import ExecutionPlanVisualizer

def test_sidebar_initialization():
    sidebar = Sidebar()
    assert sidebar is not None
    assert sidebar.is_loaded() is False

def test_sidebar_lazy_loading():
    sidebar = Sidebar()
    sidebar.load_schema('test_schema')
    assert sidebar.is_loaded() is True
    assert len(sidebar.get_tables('test_schema')) > 0

def test_sql_text_editor_initialization():
    editor = SQLTextEditor()
    assert editor is not None
    assert editor.get_text() == ""

def test_sql_text_editor_formatting():
    editor = SQLTextEditor()
    editor.set_text("SELECT * FROM test_table")
    formatted_text = editor.format_sql()
    assert formatted_text == "SELECT *\nFROM test_table;"

def test_execution_plan_visualization():
    visualizer = ExecutionPlanVisualizer()
    plan = visualizer.parse_explain("EXPLAIN SELECT * FROM test_table")
    assert plan is not None
    assert isinstance(plan, dict)  # Assuming the plan is returned as a dictionary
    assert 'Plan' in plan  # Check for expected keys in the plan output