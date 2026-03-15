import pytest
from leema.app import LeemaApp

@pytest.fixture
def app():
    """Fixture for the Leema application."""
    app = LeemaApp()
    yield app

def test_app_initialization(app):
    """Test the initialization of the Leema application."""
    assert app is not None
    assert app.title == "Leema SQL IDE"

def test_app_run(app):
    """Test running the Leema application."""
    app.run()
    assert app.is_running()  # Assuming there's a method to check if the app is running

def test_app_state_management(app):
    """Test the reactive state management of the application."""
    initial_state = app.state
    app.update_state({"key": "value"})
    assert app.state["key"] == "value"
    assert app.state != initial_state

def test_app_shutdown(app):
    """Test the shutdown process of the Leema application."""
    app.shutdown()
    assert not app.is_running()  # Assuming there's a method to check if the app is running