"""MySQL database driver implementation."""

try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
    from mysql.connector.connection import MySQLConnection
except ImportError:
    raise ImportError(
        "mysql-connector-python is not installed. Install with: pip install 'leema-sql[mysql]'")

from typing import List, Dict, Any, Optional, Tuple
from src.drivers.base import BaseEngine
import asyncio


class MySQLEngine(BaseEngine):
    """MySQL engine implementation using mysql-connector-python.

    Note: mysql-connector-python is synchronous, so we wrap calls in asyncio.to_thread
    to prevent blocking the UI.
    """

    def __init__(self, host: str, port: int, database: str, user: str, password: str, **kwargs):
        """Initialize the MySQL engine.

        Args:
            host: Database host.
            port: Database port (default 3306).
            database: Database name.
            user: Username.
            password: Password.
            **kwargs: Additional connection parameters (ssl_ca, ssl_cert, etc.).
        """
        self.connection_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password,
            **kwargs
        }
        self.connection: Optional[MySQLConnection] = None

    async def connect(self, **kwargs) -> None:
        """Establish a connection to MySQL."""
        try:
            params = {**self.connection_params, **kwargs}
            # Run synchronous connect in thread pool
            self.connection = await asyncio.to_thread(
                mysql.connector.connect,
                **params
            )
        except MySQLError as e:
            raise ConnectionError(f"Failed to connect to MySQL: {e}")
        except Exception as e:
            raise ConnectionError(f"Unexpected error connecting to MySQL: {e}")

    async def execute(self, query: str, params: Optional[Tuple] = None) -> List[Tuple[Any, ...]]:
        """Execute a SQL query."""
        if not self.connection or not self.connection.is_connected():
            raise RuntimeError(
                "Not connected to database. Call connect() first.")

        try:
            cursor = self.connection.cursor()

            # Execute in thread pool to avoid blocking
            await asyncio.to_thread(cursor.execute, query, params)

            # Fetch results
            results = await asyncio.to_thread(cursor.fetchall)
            cursor.close()

            return results
        except MySQLError as e:
            raise Exception(f"Query execution failed: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error during query execution: {e}")

    async def get_schema(self) -> Dict[str, List[Dict[str, Any]]]:
        """Retrieve the MySQL database schema."""
        if not self.connection or not self.connection.is_connected():
            raise RuntimeError(
                "Not connected to database. Call connect() first.")

        query = """
        SELECT TABLE_SCHEMA, TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')
        ORDER BY TABLE_SCHEMA, TABLE_NAME
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
        except MySQLError as e:
            raise Exception(f"Failed to retrieve schema: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error retrieving schema: {e}")

    async def get_columns(self, schema: str, table: str) -> List[Dict[str, Any]]:
        """Get columns for a specific table."""
        if not self.connection or not self.connection.is_connected():
            raise RuntimeError(
                "Not connected to database. Call connect() first.")

        query = """
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        ORDER BY ORDINAL_POSITION
        """

        try:
            cursor = self.connection.cursor()
            await asyncio.to_thread(cursor.execute, query, (schema, table))
            rows = await asyncio.to_thread(cursor.fetchall)
            cursor.close()

            return [{'name': col[0], 'type': col[1]} for col in rows]
        except MySQLError as e:
            raise Exception(f"Failed to retrieve columns: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error retrieving columns: {e}")

    async def get_explain_plan(self, query: str) -> str:
        """Get the execution plan in JSON format."""
        if not self.connection or not self.connection.is_connected():
            raise RuntimeError(
                "Not connected to database. Call connect() first.")

        explain_query = f"EXPLAIN FORMAT=JSON {query}"

        try:
            cursor = self.connection.cursor()
            await asyncio.to_thread(cursor.execute, explain_query)
            result = await asyncio.to_thread(cursor.fetchone)
            cursor.close()

            return result[0] if result else "{}"
        except MySQLError as e:
            # Fallback to traditional EXPLAIN if JSON not supported
            try:
                cursor = self.connection.cursor()
                await asyncio.to_thread(cursor.execute, f"EXPLAIN {query}")
                rows = await asyncio.to_thread(cursor.fetchall)
                cursor.close()

                # Convert to string representation
                return str(rows)
            except Exception:
                raise Exception(f"Failed to get execution plan: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error getting execution plan: {e}")

    async def close(self) -> None:
        """Close the MySQL connection."""
        if self.connection and self.connection.is_connected():
            await asyncio.to_thread(self.connection.close)
            self.connection = None

    def is_connected(self) -> bool:
        """Check if connected to MySQL."""
        return self.connection is not None and self.connection.is_connected()
