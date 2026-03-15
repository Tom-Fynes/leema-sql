"""Tests for database drivers."""

import pytest
import asyncio
from src.drivers.base import BaseEngine
from src.drivers.duckdb import DuckDBEngine


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
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
    """Test DuckDB query execution."""
    result = await duckdb_driver.execute("SELECT 1 as test")
    assert result is not None
    assert len(result) == 1
    assert result[0][0] == 1


@pytest.mark.asyncio
async def test_duckdb_execute_with_params(duckdb_driver):
    """Test DuckDB query execution with parameters."""
    result = await duckdb_driver.execute("SELECT ? as value", (42,))
    assert result is not None
    assert len(result) == 1
    assert result[0][0] == 42


@pytest.mark.asyncio
async def test_duckdb_get_schema(duckdb_driver):
    """Test DuckDB schema retrieval."""
    await duckdb_driver.execute("CREATE TABLE test_table (id INTEGER, name VARCHAR)")
    schema = await duckdb_driver.get_schema()
    assert isinstance(schema, dict)
    assert 'main' in schema
    assert any(table['name'] == 'test_table' for table in schema['main'])


@pytest.mark.asyncio
async def test_duckdb_get_columns(duckdb_driver):
    """Test DuckDB column retrieval."""
    await duckdb_driver.execute("CREATE TABLE test_table (id INTEGER, name VARCHAR, age INTEGER)")
    columns = await duckdb_driver.get_columns('main', 'test_table')
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
