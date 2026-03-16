import pytest
import yaml
from typer.testing import CliRunner
from src.app import LeemaApp
from src.config import ConnectionProfile, LeemaConfig
from src.cli import app as cli_app


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


def test_trino_profile_without_database_is_valid():
    """Trino is catalog-based; omitting database must pass validation."""
    profile = ConnectionProfile(
        name="trino-test",
        engine="trino",
        host="trino.example.com",
        port=8080,
        database="",
    )
    errors = profile.validate()
    assert errors == [], f"Expected no errors for trino without database, got: {errors}"


def test_trino_profile_with_catalog_is_valid():
    """Trino profile with a catalog/database value must also pass validation."""
    profile = ConnectionProfile(
        name="trino-catalog",
        engine="trino",
        host="trino.example.com",
        port=8080,
        database="hive",
    )
    errors = profile.validate()
    assert errors == [], f"Expected no errors for trino with catalog, got: {errors}"


def test_non_catalog_engine_without_database_is_invalid():
    """Non-catalog engines (e.g. postgres) must still require a database name."""
    default_ports = {"postgres": 5432, "mysql": 3306, "mssql": 1433, "snowflake": 443}
    for engine, port in default_ports.items():
        profile = ConnectionProfile(
            name="x",
            engine=engine,
            host="localhost",
            port=port,
            database="",
        )
        errors = profile.validate()
        assert any("database" in e.lower() for e in errors), (
            f"Expected database error for engine={engine}, got: {errors}"
        )


def test_save_raises_for_invalid_config(tmp_path):
    """LeemaConfig.save must raise ValueError when the config fails validation."""
    config = LeemaConfig()
    config.profiles["bad"] = ConnectionProfile(
        name="bad",
        engine="postgres",
        host="localhost",
        port=5432,
        database="",  # missing required database for postgres
    )
    config_file = tmp_path / "config.yaml"

    with pytest.raises(ValueError, match="validation failed"):
        config.save(str(config_file))

    assert not config_file.exists(), (
        "Config file must not be written when validation fails"
    )


def test_load_strict_false_returns_invalid_config(tmp_path):
    """LeemaConfig.load with strict=False must return the config even if invalid."""
    invalid_file = tmp_path / "invalid.yaml"
    invalid_file.write_text(
        yaml.dump(
            {
                "profiles": {
                    "pg-bad": {
                        "engine": "postgres",
                        "host": "localhost",
                        "port": 5432,
                        "database": "",  # missing for postgres
                    },
                },
                "default_profile": "pg-bad",
            }
        )
    )

    # strict=True should raise
    with pytest.raises(ValueError, match="validation failed"):
        LeemaConfig.load(str(invalid_file), strict=True)

    # strict=False should return the config for editing
    loaded = LeemaConfig.load(str(invalid_file), strict=False)
    assert "pg-bad" in loaded.profiles


# --- Connection switcher tests ---


def test_app_has_connection_select_attribute(app):
    """LeemaApp must expose a connection_select attribute for the profile dropdown."""
    assert hasattr(app, "connection_select")


def test_app_connection_select_is_none_before_compose(app):
    """connection_select must be None until the app is composed."""
    assert app.connection_select is None


def test_app_with_profiles_exposes_all_options(tmp_path):
    """The profile names in config must all be available to the connection Select widget."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.dump(
            {
                "profiles": {
                    "dev": {
                        "engine": "duckdb",
                        "host": "localhost",
                        "port": 0,
                        "database": ":memory:",
                    },
                    "prod": {
                        "engine": "duckdb",
                        "host": "localhost",
                        "port": 0,
                        "database": ":memory:",
                    },
                },
                "default_profile": "dev",
            }
        )
    )
    loaded_app = LeemaApp(config_path=str(config_file))
    assert "dev" in loaded_app.config.profiles
    assert "prod" in loaded_app.config.profiles


# --- remove-config command tests ---


def test_remove_config_deletes_file(tmp_path):
    """remove-config must delete the config file when user confirms."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({"profiles": {}, "default_profile": None}))
    assert config_file.exists()

    runner = CliRunner()
    result = runner.invoke(
        cli_app, ["remove-config", "--config", str(config_file), "--force"]
    )

    assert result.exit_code == 0, result.output
    assert not config_file.exists()
    assert "Configuration removed" in result.output


def test_remove_config_missing_file_exits_cleanly(tmp_path):
    """remove-config must report gracefully when the config file does not exist."""
    config_file = tmp_path / "nonexistent.yaml"

    runner = CliRunner()
    result = runner.invoke(
        cli_app, ["remove-config", "--config", str(config_file), "--force"]
    )

    assert result.exit_code == 0, result.output
    assert "No configuration file found" in result.output


def test_remove_config_aborted_leaves_file(tmp_path):
    """remove-config must not delete the file when the user declines confirmation."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({"profiles": {}, "default_profile": None}))

    runner = CliRunner()
    # Provide "n" as input to the confirmation prompt
    result = runner.invoke(
        cli_app, ["remove-config", "--config", str(config_file)], input="n\n"
    )

    assert result.exit_code == 0, result.output
    assert config_file.exists(), "Config file must not be deleted when user aborts"
    assert "Aborted" in result.output
