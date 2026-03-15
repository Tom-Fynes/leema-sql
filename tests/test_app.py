import pytest
import yaml
from src.app import LeemaApp
from src.config import ConnectionProfile, LeemaConfig


@pytest.fixture
def app(tmp_path):
    """Fixture for the Leema application with a temporary config."""
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


# --- Bug fix tests ---


def test_duckdb_profile_port_zero_is_valid():
    """Bug fix: DuckDB connection profiles with port=0 must pass validation."""
    profile = ConnectionProfile(
        name="local",
        engine="duckdb",
        host="localhost",
        port=0,
        database=":memory:",
    )
    errors = profile.validate()
    assert errors == [], f"Expected no errors, got: {errors}"


def test_non_duckdb_profile_port_zero_is_invalid():
    """Bug fix: port=0 is only allowed for DuckDB, not other engines."""
    profile = ConnectionProfile(
        name="pg",
        engine="postgres",
        host="localhost",
        port=0,
        database="mydb",
    )
    errors = profile.validate()
    assert any("port" in e.lower() for e in errors)


def test_negative_port_is_always_invalid():
    """Negative port numbers must never be accepted."""
    for engine in ("duckdb", "postgres", "mysql"):
        profile = ConnectionProfile(
            name="x",
            engine=engine,
            host="localhost",
            port=-1,
            database="db",
        )
        errors = profile.validate()
        assert any("port" in e.lower() for e in errors), (
            f"Expected port error for engine={engine}, got: {errors}"
        )


def test_duckdb_config_round_trip(tmp_path):
    """Bug fix: saving and reloading a DuckDB profile with port=0 must not raise."""
    config = LeemaConfig()
    config.profiles["local"] = ConnectionProfile(
        name="local",
        engine="duckdb",
        host="localhost",
        port=0,
        database=":memory:",
    )
    config.default_profile = "local"

    config_file = tmp_path / "config.yaml"
    config.save(str(config_file))

    loaded = LeemaConfig.load(str(config_file))
    assert "local" in loaded.profiles
    assert loaded.profiles["local"].port == 0
