"""DuckDB database driver implementation."""

import duckdb
import time
from typing import List, Dict, Any, Optional, Tuple
from src.drivers.base import BaseEngine, QueryResult


class DuckDBEngine(BaseEngine):
    """DuckDB in-process engine implementation.

    DuckDB is synchronous but we wrap it in async methods for consistency.
    """

    def __init__(self, database: str = ':memory:', **kwargs):
        """Initialize the DuckDB engine.

        Args:
            database: Path to database file or ':memory:' for in-memory database.
            **kwargs: Ignored extra keyword arguments (e.g., host, port, username)
                      accepted for a uniform construction interface.
        """
        self.database = database
        self.connection: Optional[duckdb.DuckDBPyConnection] = None

    async def connect(self, **kwargs) -> None:
        """Establish a connection to DuckDB."""
        try:
            self.connection = duckdb.connect(self.database)
        except Exception as e:
            raise ConnectionError(f"Failed to connect to DuckDB: {e}")

    async def execute(self, query: str, params: Optional[Tuple] = None) -> QueryResult:
        """Execute a SQL query."""
        if not self.connection:
            raise RuntimeError(
                "Not connected to database. Call connect() first.")

        try:
            start_time = time.time()
            if params:
                result = self.connection.execute(query, list(params))
            else:
                result = self.connection.execute(query)

            rows = result.fetchall()
            columns = [desc[0] for desc in result.description] if result.description else []
            execution_time = time.time() - start_time
            return QueryResult(
                columns=columns,
                rows=rows,
                row_count=len(rows),
                execution_time=execution_time,
            )
        except Exception as e:
            raise Exception(f"Query execution failed: {e}")

    async def get_schema(self) -> Dict[str, List[Dict[str, Any]]]:
        """Retrieve the DuckDB schema."""
        if not self.connection:
            raise RuntimeError(
                "Not connected to database. Call connect() first.")

        try:
            tables_result = self.connection.execute(
                "SELECT table_schema, table_name FROM information_schema.tables "
                "WHERE table_schema NOT IN ('information_schema', 'pg_catalog')"
            ).fetchall()

            schema: Dict[str, List[Dict[str, Any]]] = {}

            for table_schema, table_name in tables_result:
                if table_schema not in schema:
                    schema[table_schema] = []

                # Don't load columns immediately - support lazy loading
                schema[table_schema].append({
                    'name': table_name,
                    'columns': []  # Will be loaded lazily
                })

            return schema
        except Exception as e:
            raise Exception(f"Failed to retrieve schema: {e}")

    async def get_databases(self) -> List[str]:
        """Get list of available databases (catalogs in DuckDB)."""
        if not self.connection:
            raise RuntimeError(
                "Not connected to database. Call connect() first.")

        try:
            rows = self.connection.execute(
                "SELECT DISTINCT catalog_name FROM information_schema.schemata ORDER BY catalog_name"
            ).fetchall()
            return [row[0] for row in rows]
        except Exception as e:
            raise Exception(f"Failed to retrieve databases: {e}")

    async def get_schemas(self, database: str) -> List[str]:
        """Get list of schemas in DuckDB."""
        if not self.connection:
            raise RuntimeError(
                "Not connected to database. Call connect() first.")

        try:
            rows = self.connection.execute(
                "SELECT schema_name FROM information_schema.schemata "
                "WHERE schema_name NOT IN ('information_schema', 'pg_catalog') "
                "ORDER BY schema_name"
            ).fetchall()
            return [row[0] for row in rows]
        except Exception as e:
            raise Exception(f"Failed to retrieve schemas: {e}")

    async def get_tables(self, database: str, schema: str) -> List[str]:
        """Get list of tables in a schema."""
        if not self.connection:
            raise RuntimeError(
                "Not connected to database. Call connect() first.")

        try:
            rows = self.connection.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = ? ORDER BY table_name",
                [schema]
            ).fetchall()
            return [row[0] for row in rows]
        except Exception as e:
            raise Exception(f"Failed to retrieve tables: {e}")

    async def get_columns(self, database: str, schema: str, table: str) -> List[Dict[str, Any]]:
        """Get columns for a specific table."""
        if not self.connection:
            raise RuntimeError(
                "Not connected to database. Call connect() first.")

        try:
            columns_result = self.connection.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_schema = ? AND table_name = ? "
                "ORDER BY ordinal_position",
                [schema, table]
            ).fetchall()

            return [{'name': col[0], 'type': col[1]} for col in columns_result]
        except Exception as e:
            raise Exception(f"Failed to retrieve columns: {e}")

    async def get_explain_plan(self, query: str) -> str:
        """Get the execution plan."""
        if not self.connection:
            raise RuntimeError(
                "Not connected to database. Call connect() first.")

        try:
            result = self.connection.execute(f"EXPLAIN {query}").fetchall()
            plan_parts = []
            for row in result:
                if len(row) >= 2:
                    plan_parts.append(str(row[1]))
            return "\n".join(plan_parts) if plan_parts else ""
        except Exception as e:
            raise Exception(f"Failed to get execution plan: {e}")

    async def close(self) -> None:
        """Close the DuckDB connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def is_connected(self) -> bool:
        """Check if connected to DuckDB."""
        return self.connection is not None

