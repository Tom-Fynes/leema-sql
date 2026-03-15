"""Trino (formerly Presto SQL) database driver implementation."""

try:
    from trino.dbapi import connect
    from trino.exceptions import TrinoUserError, TrinoQueryError
except ImportError:
    raise ImportError(
        "trino is not installed. Install with: pip install 'leema-sql[trino]'")

from typing import List, Dict, Any, Optional, Tuple
from src.drivers.base import BaseEngine
import asyncio


class TrinoEngine(BaseEngine):
    """Trino engine implementation using trino-python-client.

    Trino is designed for distributed SQL queries across multiple data sources.
    Note: trino client is synchronous, so we wrap calls in asyncio.to_thread.
    """

    def __init__(
        self,
        host: str,
        port: int,
        catalog: str,
        schema: str,
        user: str,
        http_scheme: str = "http",
        **kwargs
    ):
        """Initialize the Trino engine.

        Args:
            host: Trino coordinator host.
            port: Trino coordinator port (default 8080).
            catalog: Catalog name (e.g., 'hive', 'postgresql').
            schema: Schema/database name.
            user: Username.
            http_scheme: 'http' or 'https'.
            **kwargs: Additional connection parameters (auth, cert, etc.).
        """
        self.connection_params = {
            'host': host,
            'port': port,
            'catalog': catalog,
            'schema': schema,
            'user': user,
            'http_scheme': http_scheme,
            **kwargs
        }
        self.connection = None
        self.catalog = catalog
        self.schema = schema

    async def connect(self, **kwargs) -> None:
        """Establish a connection to Trino."""
        try:
            params = {**self.connection_params, **kwargs}
            # Run synchronous connect in thread pool
            self.connection = await asyncio.to_thread(connect, **params)
        except (TrinoUserError, TrinoQueryError) as e:
            raise ConnectionError(f"Failed to connect to Trino: {e}")
        except Exception as e:
            raise ConnectionError(f"Unexpected error connecting to Trino: {e}")

    async def execute(self, query: str, params: Optional[Tuple] = None) -> List[Tuple[Any, ...]]:
        """Execute a SQL query."""
        if not self.connection:
            raise RuntimeError(
                "Not connected to database. Call connect() first.")

        try:
            cursor = self.connection.cursor()

            # Execute in thread pool to avoid blocking
            if params:
                await asyncio.to_thread(cursor.execute, query, params)
            else:
                await asyncio.to_thread(cursor.execute, query)

            # Fetch results
            results = await asyncio.to_thread(cursor.fetchall)
            cursor.close()

            return results
        except (TrinoUserError, TrinoQueryError) as e:
            raise Exception(f"Query execution failed: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error during query execution: {e}")

    async def get_schema(self) -> Dict[str, List[Dict[str, Any]]]:
        """Retrieve the Trino catalog schema."""
        if not self.connection:
            raise RuntimeError(
                "Not connected to database. Call connect() first.")

        query = f"""
        SELECT table_schema, table_name
        FROM {self.catalog}.information_schema.tables
        WHERE table_catalog = '{self.catalog}'
        ORDER BY table_schema, table_name
        """

        try:
            cursor = self.connection.cursor()
            await asyncio.to_thread(cursor.execute, query)
            rows = await asyncio.to_thread(cursor.fetchall)
            cursor.close()

            schema: Dict[str, List[Dict[str, Any]]] = {}
            for table_schema, table_name in rows:
                if table_schema not in schema:
                    schema[table_schema] = []

                schema[table_schema].append({
                    'name': table_name,
                    'columns': []  # Will be loaded lazily
                })

            return schema
        except (TrinoUserError, TrinoQueryError) as e:
            raise Exception(f"Failed to retrieve schema: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error retrieving schema: {e}")

    async def get_columns(self, schema: str, table: str) -> List[Dict[str, Any]]:
        """Get columns for a specific table."""
        if not self.connection:
            raise RuntimeError(
                "Not connected to database. Call connect() first.")

        query = f"""
        SELECT column_name, data_type
        FROM {self.catalog}.information_schema.columns
        WHERE table_schema = '{schema}' AND table_name = '{table}'
        ORDER BY ordinal_position
        """

        try:
            cursor = self.connection.cursor()
            await asyncio.to_thread(cursor.execute, query)
            rows = await asyncio.to_thread(cursor.fetchall)
            cursor.close()

            return [{'name': col[0], 'type': col[1]} for col in rows]
        except (TrinoUserError, TrinoQueryError) as e:
            raise Exception(f"Failed to retrieve columns: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error retrieving columns: {e}")

    async def get_explain_plan(self, query: str) -> str:
        """Get the execution plan in text format."""
        if not self.connection:
            raise RuntimeError(
                "Not connected to database. Call connect() first.")

        explain_query = f"EXPLAIN {query}"

        try:
            cursor = self.connection.cursor()
            await asyncio.to_thread(cursor.execute, explain_query)
            rows = await asyncio.to_thread(cursor.fetchall)
            cursor.close()

            # Combine all rows into a single string
            return "\n".join(str(row[0]) for row in rows)
        except (TrinoUserError, TrinoQueryError) as e:
            raise Exception(f"Failed to get execution plan: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error getting execution plan: {e}")

    async def close(self) -> None:
        """Close the Trino connection."""
        if self.connection:
            await asyncio.to_thread(self.connection.close)
            self.connection = None

    def is_connected(self) -> bool:
        """Check if connected to Trino."""
        return self.connection is not None
