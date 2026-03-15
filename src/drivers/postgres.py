"""PostgreSQL database driver implementation."""

try:
    import psycopg
    from psycopg import AsyncConnection
except ImportError:
    raise ImportError(
        "psycopg is not installed. Install with: pip install 'leema-sql[postgres]'")

from typing import List, Dict, Any, Optional, Tuple
from src.drivers.base import BaseEngine


class PostgresEngine(BaseEngine):
    """PostgreSQL engine implementation using psycopg (async)."""

    def __init__(self, host: str, port: int, database: str, user: str, password: str, **kwargs):
        """Initialize the PostgreSQL engine.

        Args:
            host: Database host.
            port: Database port.
            database: Database name.
            user: Username.
            password: Password.
            **kwargs: Additional connection parameters.
        """
        self.connection_params = {
            'host': host,
            'port': port,
            'dbname': database,
            'user': user,
            'password': password,
            **kwargs
        }
        self.connection: Optional[AsyncConnection] = None

    async def connect(self, **kwargs) -> None:
        """Establish an async connection to PostgreSQL."""
        try:
            params = {**self.connection_params, **kwargs}
            self.connection = await AsyncConnection.connect(**params)
        except Exception as e:
            raise ConnectionError(f"Failed to connect to PostgreSQL: {e}")

    async def execute(self, query: str, params: Optional[Tuple] = None) -> List[Tuple[Any, ...]]:
        """Execute a SQL query asynchronously."""
        if not self.connection:
            raise RuntimeError(
                "Not connected to database. Call connect() first.")

        try:
            async with self.connection.cursor() as cursor:
                await cursor.execute(query, params)
                return await cursor.fetchall()
        except Exception as e:
            raise Exception(f"Query execution failed: {e}")

    async def get_schema(self) -> Dict[str, List[Dict[str, Any]]]:
        """Retrieve the PostgreSQL database schema."""
        if not self.connection:
            raise RuntimeError(
                "Not connected to database. Call connect() first.")

        query = """
        SELECT DISTINCT table_schema, table_name
        FROM information_schema.tables
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY table_schema, table_name
        """

        try:
            async with self.connection.cursor() as cursor:
                await cursor.execute(query)
                rows = await cursor.fetchall()

            schema: Dict[str, List[Dict[str, Any]]] = {}
            for table_schema, table_name in rows:
                if table_schema not in schema:
                    schema[table_schema] = []

                schema[table_schema].append({
                    'name': table_name,
                    'columns': []  # Will be loaded lazily
                })

            return schema
        except Exception as e:
            raise Exception(f"Failed to retrieve schema: {e}")

    async def get_columns(self, schema: str, table: str) -> List[Dict[str, Any]]:
        """Get columns for a specific table."""
        if not self.connection:
            raise RuntimeError(
                "Not connected to database. Call connect() first.")

        query = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
        """

        try:
            async with self.connection.cursor() as cursor:
                await cursor.execute(query, (schema, table))
                rows = await cursor.fetchall()

            return [{'name': col[0], 'type': col[1]} for col in rows]
        except Exception as e:
            raise Exception(f"Failed to retrieve columns: {e}")

    async def get_explain_plan(self, query: str) -> str:
        """Get the execution plan in JSON format."""
        if not self.connection:
            raise RuntimeError(
                "Not connected to database. Call connect() first.")

        explain_query = f"EXPLAIN (FORMAT JSON) {query}"

        try:
            async with self.connection.cursor() as cursor:
                await cursor.execute(explain_query)
                result = await cursor.fetchone()
                return result[0] if result else "{}"
        except Exception as e:
            raise Exception(f"Failed to get execution plan: {e}")

    async def close(self) -> None:
        """Close the PostgreSQL connection."""
        if self.connection:
            await self.connection.close()
            self.connection = None

    def is_connected(self) -> bool:
        """Check if connected to PostgreSQL."""
        return self.connection is not None and not self.connection.closed
