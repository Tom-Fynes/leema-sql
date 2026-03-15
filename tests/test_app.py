import pytest
from src.app import LeemaApp


@pytest.fixture
def app(tmp_path):
    """Fixture for the Leema application with a temporary config."""
    import yaml
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({"profiles": {}, "default_profile": None}))
    app = LeemaApp(config_path=str(config_file))
    yield app


def test_app_initialization(app):
    """Test the initialization of the Leema application."""
    assert app is not None
    assert app.TITLE == "Leema SQL IDE"


def test_app_no_engine_on_init(app):
    """Test that there is no active engine on initialization."""
    assert app._current_engine is None


def test_app_explain_mode_default(app):
    """Test that EXPLAIN mode is off by default."""
    assert app._explain_mode is False


def test_app_explain_mode_toggle(app):
    """Test toggling EXPLAIN mode."""
    assert app._explain_mode is False
    app._explain_mode = True
    assert app._explain_mode is True
    app._explain_mode = False
    assert app._explain_mode is False
