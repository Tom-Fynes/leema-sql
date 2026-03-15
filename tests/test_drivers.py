"""Tests for database drivers."""

import pytest
import pytest_asyncio
import asyncio
from src.drivers.base import BaseEngine, QueryResult
from src.drivers.duckdb import DuckDBEngine


@pytest_asyncio.fixture
async def duckdb_driver():
    """Create a DuckDB driver instance."""
    driver = DuckDBEngine(':memory:')
    await driver.connect()
    yield driver
    await driver.close()


@pytest.mark.asyncio
async def test_duckdb_connect():
    """Test DuckDB connection."""
    driver = DuckDBEngine(':memory:')
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
    assert result.columns == ['test']
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
    assert 'main' in schema
    assert any(table['name'] == 'test_table' for table in schema['main'])


@pytest.mark.asyncio
async def test_duckdb_get_databases(duckdb_driver):
    """Test DuckDB database (catalog) listing."""
    databases = await duckdb_driver.get_databases()
    assert isinstance(databases, list)
    assert len(databases) > 0


@pytest.mark.asyncio
async def test_duckdb_get_schemas(duckdb_driver):
    """Test DuckDB schema listing."""
    schemas = await duckdb_driver.get_schemas('memory')
    assert isinstance(schemas, list)
    assert 'main' in schemas


@pytest.mark.asyncio
async def test_duckdb_get_tables(duckdb_driver):
    """Test DuckDB table listing."""
    await duckdb_driver.execute("CREATE TABLE test_table2 (id INTEGER)")
    tables = await duckdb_driver.get_tables('memory', 'main')
    assert isinstance(tables, list)
    assert 'test_table2' in tables


@pytest.mark.asyncio
async def test_duckdb_get_columns(duckdb_driver):
    """Test DuckDB column retrieval with 3-arg signature."""
    await duckdb_driver.execute("CREATE TABLE test_table (id INTEGER, name VARCHAR, age INTEGER)")
    columns = await duckdb_driver.get_columns('memory', 'main', 'test_table')
    assert len(columns) == 3
    assert columns[0]['name'] == 'id'
    assert columns[1]['name'] == 'name'
    assert columns[2]['name'] == 'age'


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
    driver = DuckDBEngine(':memory:')

    with pytest.raises(RuntimeError, match="Not connected"):
        await driver.execute("SELECT 1")

