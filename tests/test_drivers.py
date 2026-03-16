"""Tests for database drivers."""

import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch
from src.drivers.base import QueryResult
from src.drivers.duckdb import DuckDBEngine
from src.drivers import get_available_drivers


@pytest_asyncio.fixture
async def duckdb_driver():
    """Create a DuckDB driver instance."""
    driver = DuckDBEngine(":memory:")
    await driver.connect()
    yield driver
    await driver.close()


@pytest.mark.asyncio
async def test_duckdb_connect():
    """Test DuckDB connection."""
    driver = DuckDBEngine(":memory:")
    await driver.connect()
    assert driver.is_connected()
    assert driver.connection is not None
    await driver.close()
    assert not driver.is_connected()


@pytest.mark.asyncio
async def test_duckdb_execute(duckdb_driver):
    """Test DuckDB query execution returns a QueryResult."""
    result = await duckdb_driver.execute("SELECT 1 as test")
    assert isinstance(result, QueryResult)
    assert result.row_count == 1
    assert result.columns == ["test"]
    assert result.rows[0][0] == 1
    assert result.execution_time >= 0


@pytest.mark.asyncio
async def test_duckdb_execute_with_params(duckdb_driver):
    """Test DuckDB query execution with parameters."""
    result = await duckdb_driver.execute("SELECT ? as value", (42,))
    assert isinstance(result, QueryResult)
    assert result.row_count == 1
    assert result.rows[0][0] == 42


@pytest.mark.asyncio
async def test_duckdb_get_schema(duckdb_driver):
    """Test DuckDB schema retrieval."""
    await duckdb_driver.execute("CREATE TABLE test_table (id INTEGER, name VARCHAR)")
    schema = await duckdb_driver.get_schema()
    assert isinstance(schema, dict)
    assert "main" in schema
    assert any(table["name"] == "test_table" for table in schema["main"])


@pytest.mark.asyncio
async def test_duckdb_get_databases(duckdb_driver):
    """Test DuckDB database (catalog) listing."""
    databases = await duckdb_driver.get_databases()
    assert isinstance(databases, list)
    assert len(databases) > 0


@pytest.mark.asyncio
async def test_duckdb_get_schemas(duckdb_driver):
    """Test DuckDB schema listing."""
    schemas = await duckdb_driver.get_schemas("memory")
    assert isinstance(schemas, list)
    assert "main" in schemas


@pytest.mark.asyncio
async def test_duckdb_get_tables(duckdb_driver):
    """Test DuckDB table listing."""
    await duckdb_driver.execute("CREATE TABLE test_table2 (id INTEGER)")
    tables = await duckdb_driver.get_tables("memory", "main")
    assert isinstance(tables, list)
    assert "test_table2" in tables


@pytest.mark.asyncio
async def test_duckdb_get_columns(duckdb_driver):
    """Test DuckDB column retrieval with 3-arg signature."""
    await duckdb_driver.execute(
        "CREATE TABLE test_table (id INTEGER, name VARCHAR, age INTEGER)"
    )
    columns = await duckdb_driver.get_columns("memory", "main", "test_table")
    assert len(columns) == 3
    assert columns[0]["name"] == "id"
    assert columns[1]["name"] == "name"
    assert columns[2]["name"] == "age"


@pytest.mark.asyncio
async def test_duckdb_explain_plan(duckdb_driver):
    """Test DuckDB execution plan."""
    await duckdb_driver.execute("CREATE TABLE test_table (id INTEGER, name VARCHAR)")
    plan = await duckdb_driver.get_explain_plan("SELECT * FROM test_table")
    assert plan is not None
    assert len(plan) > 0


@pytest.mark.asyncio
async def test_duckdb_not_connected_error():
    """Test that operations fail when not connected."""
    driver = DuckDBEngine(":memory:")

    with pytest.raises(RuntimeError, match="Not connected"):
        await driver.execute("SELECT 1")


# --- Bug fix tests ---


def test_get_available_drivers_returns_dict():
    """Bug fix: get_available_drivers must be importable and return a dict."""
    drivers = get_available_drivers()
    assert isinstance(drivers, dict)
    assert len(drivers) > 0


def test_get_available_drivers_contains_duckdb():
    """Bug fix: DuckDB is always available and must appear in the driver registry."""
    drivers = get_available_drivers()
    assert "duckdb" in drivers


def test_get_available_drivers_returns_copy():
    """Bug fix: mutating the returned dict must not affect the registry."""
    drivers = get_available_drivers()
    drivers.clear()
    assert "duckdb" in get_available_drivers()


@pytest.mark.asyncio
async def test_duckdb_explain_plan_returns_plan_text():
    """Bug fix: get_explain_plan must return actual plan text, not the column name."""
    driver = DuckDBEngine(":memory:")
    await driver.connect()
    await driver.execute("CREATE TABLE t (id INTEGER, name VARCHAR)")
    plan = await driver.get_explain_plan("SELECT * FROM t")
    await driver.close()

    # Must not be just the column key name
    assert plan.strip() != "physical_plan"
    # Must contain meaningful plan content (DuckDB renders ASCII box-drawing art)
    assert len(plan.strip()) > 20


# --- Trino identifier-quoting tests ---


@pytest.mark.asyncio
async def test_trino_get_schemas_quotes_database():
    """Bug fix: get_schemas must send SHOW SCHEMAS FROM \"<db>\" (quoted identifier)."""
    from src.drivers.trino import TrinoEngine

    engine = TrinoEngine(
        host="localhost", port=8080, catalog="hive", schema="default", username="user"
    )
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [("public",)]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    engine.connection = mock_conn

    with patch("asyncio.to_thread", side_effect=lambda fn, *a, **kw: fn(*a, **kw)):
        await engine.get_schemas("my-catalog")

    executed_sql = mock_cursor.execute.call_args[0][0]
    assert '"my-catalog"' in executed_sql, (
        f"Expected quoted identifier in SQL, got: {executed_sql}"
    )


@pytest.mark.asyncio
async def test_trino_get_tables_quotes_database_and_schema():
    """Bug fix: get_tables must send SHOW TABLES FROM \"<db>\".\"<schema>\" (quoted)."""
    from src.drivers.trino import TrinoEngine

    engine = TrinoEngine(
        host="localhost", port=8080, catalog="hive", schema="default", username="user"
    )
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [("orders",)]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    engine.connection = mock_conn

    with patch("asyncio.to_thread", side_effect=lambda fn, *a, **kw: fn(*a, **kw)):
        await engine.get_tables("my-catalog", "my-schema")

    executed_sql = mock_cursor.execute.call_args[0][0]
    assert '"my-catalog"' in executed_sql, (
        f"Expected quoted catalog in SQL, got: {executed_sql}"
    )
    assert '"my-schema"' in executed_sql, (
        f"Expected quoted schema in SQL, got: {executed_sql}"
    )


@pytest.mark.asyncio
async def test_trino_get_columns_quotes_database_and_parameterises_values():
    """Bug fix: get_columns must quote the catalog identifier and parameterise schema/table."""
    from src.drivers.trino import TrinoEngine

    engine = TrinoEngine(
        host="localhost", port=8080, catalog="hive", schema="default", username="user"
    )
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [("id", "INTEGER")]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    engine.connection = mock_conn

    with patch("asyncio.to_thread", side_effect=lambda fn, *a, **kw: fn(*a, **kw)):
        await engine.get_columns("my-catalog", "my-schema", "my-table")

    executed_sql = mock_cursor.execute.call_args[0][0]
    call_positional_args = mock_cursor.execute.call_args[0]
    executed_params = call_positional_args[1] if len(call_positional_args) > 1 else None

    # Catalog must be quoted as identifier, not injected as string literal
    assert '"my-catalog"' in executed_sql, (
        f"Expected quoted catalog identifier, got: {executed_sql}"
    )
    # Schema and table must be passed as parameters, not interpolated
    assert "'my-schema'" not in executed_sql, (
        f"schema should not be string-interpolated into SQL, got: {executed_sql}"
    )
    assert "'my-table'" not in executed_sql, (
        f"table should not be string-interpolated into SQL, got: {executed_sql}"
    )
    assert executed_params == ["my-schema", "my-table"], (
        f"Expected parameterised values, got: {executed_params}"
    )


# --- Trino constructor / connection-parameter tests ---


def test_trino_accepts_database_alias_for_catalog():
    """Bug fix: TrinoEngine must accept 'database' as an alias for 'catalog'."""
    from src.drivers.trino import TrinoEngine

    engine = TrinoEngine(host="localhost", port=8080, database="hive", username="user")
    assert engine.connection_params["catalog"] == "hive"
    assert engine.catalog == "hive"


def test_trino_catalog_takes_priority_over_database():
    """When both catalog and database are supplied, catalog wins."""
    from src.drivers.trino import TrinoEngine

    engine = TrinoEngine(
        host="localhost",
        port=8080,
        catalog="explicit_catalog",
        database="ignored",
        username="user",
    )
    assert engine.connection_params["catalog"] == "explicit_catalog"


def test_trino_schema_defaults_to_default():
    """When schema is omitted, connection_params must include schema='default'."""
    from src.drivers.trino import TrinoEngine

    engine = TrinoEngine(host="localhost", port=8080, database="hive", username="user")
    assert engine.connection_params["schema"] == "default"


def test_trino_password_creates_basic_authentication():
    """Bug fix: passing password= must create a BasicAuthentication auth object."""
    from src.drivers.trino import TrinoEngine
    from trino.auth import BasicAuthentication

    engine = TrinoEngine(
        host="localhost",
        port=8080,
        database="hive",
        username="user",
        password="secret",
    )
    assert "auth" in engine.connection_params
    assert isinstance(engine.connection_params["auth"], BasicAuthentication)
    # password must NOT appear as a raw key
    assert "password" not in engine.connection_params


def test_trino_ssl_true_upgrades_http_scheme_to_https():
    """Bug fix: passing ssl=True must set http_scheme to 'https'."""
    from src.drivers.trino import TrinoEngine

    engine = TrinoEngine(
        host="localhost",
        port=8080,
        database="hive",
        username="user",
        ssl=True,
    )
    assert engine.connection_params["http_scheme"] == "https"
    # ssl flag must NOT be forwarded to the trino client
    assert "ssl" not in engine.connection_params


def test_trino_cert_path_and_key_path_create_certificate_authentication():
    """cert_path + key_path must create a CertificateAuthentication auth object."""
    from src.drivers.trino import TrinoEngine
    from trino.auth import CertificateAuthentication

    engine = TrinoEngine(
        host="localhost",
        port=8080,
        database="hive",
        username="user",
        ssl=True,
        cert_path="/path/to/cert.pem",
        key_path="/path/to/key.pem",
    )
    assert "auth" in engine.connection_params
    assert isinstance(engine.connection_params["auth"], CertificateAuthentication)
    # raw cert_path / key_path must NOT be forwarded to the trino client
    assert "cert_path" not in engine.connection_params
    assert "key_path" not in engine.connection_params


def test_trino_cert_auth_takes_priority_over_password():
    """Certificate auth must take priority when both password and cert paths are given."""
    from src.drivers.trino import TrinoEngine
    from trino.auth import CertificateAuthentication

    engine = TrinoEngine(
        host="localhost",
        port=8080,
        database="hive",
        username="user",
        password="secret",
        ssl=True,
        cert_path="/path/to/cert.pem",
        key_path="/path/to/key.pem",
    )
    assert isinstance(engine.connection_params["auth"], CertificateAuthentication)


def test_trino_password_auto_upgrades_http_scheme_to_https():
    """Password (BasicAuthentication) must auto-upgrade http_scheme to 'https'.

    Trino requires HTTPS for password authentication.  Even when ssl=False is
    set in the connection profile, if a password is supplied the engine must
    upgrade to HTTPS so the connection succeeds.
    """
    from src.drivers.trino import TrinoEngine

    engine = TrinoEngine(
        host="localhost",
        port=8080,
        database="hive",
        username="user",
        password="secret",
        ssl=False,
    )
    assert engine.connection_params["http_scheme"] == "https"


@pytest.mark.asyncio
async def test_trino_execute_raises_clear_error_on_https_mismatch():
    """A '400 plain HTTP request sent to HTTPS port' error must surface as a
    ConnectionError with an actionable 'Set ssl: true' hint."""
    from src.drivers.trino import TrinoEngine

    engine = TrinoEngine(host="localhost", port=8080, database="hive", username="user")
    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = Exception(
        "error 400: b'<html>\\r\\n<head><title>400 The plain HTTP request was "
        "sent to HTTPS port</title></head>'"
    )
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    engine.connection = mock_conn

    with pytest.raises(ConnectionError, match="ssl.*true|Set ssl"):
        with patch("asyncio.to_thread", side_effect=lambda fn, *a, **kw: fn(*a, **kw)):
            await engine.execute("SELECT 1")


# --- Snowflake identifier-quoting tests ---


@pytest.mark.asyncio
async def test_snowflake_get_schemas_quotes_database():
    """Bug fix: get_schemas must issue USE DATABASE \"<db>\" (quoted identifier)."""
    from src.drivers.snowflake import SnowflakeEngine

    engine = SnowflakeEngine(
        host="account.snowflakecomputing.com",
        port=443,
        database="mydb",
        username="user",
    )
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("created_on", "PUBLIC", "mydb", "SCHEMA", "MANAGED ACCESS", "1")
    ]
    engine._cursor = mock_cursor

    with patch("asyncio.to_thread", side_effect=lambda fn, *a, **kw: fn(*a, **kw)):
        await engine.get_schemas("my-database")

    first_call_sql = mock_cursor.execute.call_args_list[0][0][0]
    assert '"my-database"' in first_call_sql, (
        f"Expected quoted database identifier in USE DATABASE, got: {first_call_sql}"
    )


@pytest.mark.asyncio
async def test_snowflake_get_tables_quotes_database_and_schema():
    """Bug fix: get_tables must quote identifiers in USE DATABASE and USE SCHEMA."""
    from src.drivers.snowflake import SnowflakeEngine

    engine = SnowflakeEngine(
        host="account.snowflakecomputing.com",
        port=443,
        database="mydb",
        username="user",
    )
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    engine._cursor = mock_cursor

    with patch("asyncio.to_thread", side_effect=lambda fn, *a, **kw: fn(*a, **kw)):
        await engine.get_tables("my-database", "my-schema")

    calls = [c[0][0] for c in mock_cursor.execute.call_args_list]
    use_db_call = calls[0]
    use_schema_call = calls[1]
    assert '"my-database"' in use_db_call, (
        f"Expected quoted identifier in USE DATABASE, got: {use_db_call}"
    )
    assert '"my-schema"' in use_schema_call, (
        f"Expected quoted identifier in USE SCHEMA, got: {use_schema_call}"
    )


@pytest.mark.asyncio
async def test_snowflake_get_columns_quotes_three_part_name():
    """Bug fix: get_columns must use \"db\".\"schema\".\"table\" in DESCRIBE TABLE."""
    from src.drivers.snowflake import SnowflakeEngine

    engine = SnowflakeEngine(
        host="account.snowflakecomputing.com",
        port=443,
        database="mydb",
        username="user",
    )
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("id", "NUMBER(38,0)", "COLUMN", "Y", None, "N", None)
    ]
    engine._cursor = mock_cursor

    with patch("asyncio.to_thread", side_effect=lambda fn, *a, **kw: fn(*a, **kw)):
        await engine.get_columns("my-db", "my-schema", "my-table")

    executed_sql = mock_cursor.execute.call_args[0][0]
    assert '"my-db"."my-schema"."my-table"' in executed_sql, (
        f"Expected fully-quoted three-part name, got: {executed_sql}"
    )
