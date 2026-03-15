"""Microsoft SQL Server database driver implementation."""

try:
    import pymssql
    from pymssql import Error as MSSQLError
except ImportError:
    raise ImportError(
        "pymssql is not installed. Install with: pip install 'leema-sql[mssql]'")

from typing import List, Dict, Any, Optional, Tuple
from src.drivers.base import BaseEngine
import asyncio


class MSSQLEngine(BaseEngine):
    """Microsoft SQL Server engine implementation using pymssql.

    Supports:
    - Password authentication
    - Windows authentication (Integrated Security)
    - SSL/TLS connections

    Note: pymssql is synchronous, so we wrap calls in asyncio.to_thread.
    """

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: Optional[str] = None,
        password: Optional[str] = None,
        use_windows_auth: bool = False,
        **kwargs
    ):
        """Initialize the SQL Server engine.

        Args:
            host: Database host.
            port: Database port (default 1433).
            database: Database name.
            user: Username (not needed for Windows auth).
            password: Password (not needed for Windows auth).
            use_windows_auth: Use Windows authentication instead of SQL auth.
            **kwargs: Additional connection parameters (tds_version, charset, etc.).
        """
        self.connection_params = {
            'server': host,
            'port': port,
            'database': database,
            **kwargs
        }

        if use_windows_auth:
            # Windows authentication - don't pass user/password
            self.connection_params['trusted'] = True
        else:
            if not user or not password:
                raise ValueError(
                    "Username and password required for SQL authentication")
            self.connection_params['user'] = user
            self.connection_params['password'] = password

        self.connection: Optional[pymssql.Connection] = None

    async def connect(self, **kwargs) -> None:
        """Establish a connection to SQL Server."""
        try:
            params = {**self.connection_params, **kwargs}
            # Run synchronous connect in thread pool
            self.connection = await asyncio.to_thread(
                pymssql.connect,
                **params
            )
        except MSSQLError as e:
            raise ConnectionError(f"Failed to connect to SQL Server: {e}")
        except Exception as e:
            raise ConnectionError(
                f"Unexpected error connecting to SQL Server: {e}")

    async def execute(self, query: str, params: Optional[Tuple] = None) -> List[Tuple[Any, ...]]:
        """Execute a SQL query."""
        if not self.connection:
            raise RuntimeError(
                "Not connected to database. Call connect() first.")

        try:
            cursor = self.connection.cursor()

            # Execute in thread pool to avoid blocking
            await asyncio.to_thread(cursor.execute, query, params)

            # Fetch results if this was a SELECT
            try:
                results = await asyncio.to_thread(cursor.fetchall)
            except Exception:
                # Not a SELECT query, return empty list
                results = []

            cursor.close()
            return results
        except MSSQLError as e:
            raise Exception(f"Query execution failed: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error during query execution: {e}")

    async def get_schema(self) -> Dict[str, List[Dict[str, Any]]]:
        """Retrieve the SQL Server database schema."""
        if not self.connection:
            raise RuntimeError(
                "Not connected to database. Call connect() first.")

        query = """
        SELECT 
            SCHEMA_NAME(schema_id) AS schema_name,
            name AS table_name
        FROM sys.tables
        ORDER BY schema_name, table_name
        """

        try:
            cursor = self.connection.cursor()
            await asyncio.to_thread(cursor.execute, query)
            rows = await asyncio.to_thread(cursor.fetchall)
            cursor.close()

            schema: Dict[str, List[Dict[str, Any]]] = {}
            for schema_name, table_name in rows:
                if schema_name not in schema:
                    schema[schema_name] = []

                schema[schema_name].append({
                    'name': table_name,
                    'columns': []  # Will be loaded lazily
                })

            return schema
        except MSSQLError as e:
            raise Exception(f"Failed to retrieve schema: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error retrieving schema: {e}")

    async def get_columns(self, schema: str, table: str) -> List[Dict[str, Any]]:
        """Get columns for a specific table."""
        if not self.connection:
            raise RuntimeError(
                "Not connected to database. Call connect() first.")

        query = """
        SELECT 
            c.name AS column_name,
            TYPE_NAME(c.user_type_id) AS data_type
        FROM sys.columns c
        JOIN sys.tables t ON c.object_id = t.object_id
        JOIN sys.schemas s ON t.schema_id = s.schema_id
        WHERE s.name = %s AND t.name = %s
        ORDER BY c.column_id
        """

        try:
            cursor = self.connection.cursor()
            await asyncio.to_thread(cursor.execute, query, (schema, table))
            rows = await asyncio.to_thread(cursor.fetchall)
            cursor.close()

            return [{'name': col[0], 'type': col[1]} for col in rows]
        except MSSQLError as e:
            raise Exception(f"Failed to retrieve columns: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error retrieving columns: {e}")

    async def get_explain_plan(self, query: str) -> str:
        """Get the execution plan in XML format."""
        if not self.connection:
            raise RuntimeError(
                "Not connected to database. Call connect() first.")

        try:
            cursor = self.connection.cursor()

            # Turn on XML execution plan
            await asyncio.to_thread(cursor.execute, "SET SHOWPLAN_XML ON")

            # Get the plan
            await asyncio.to_thread(cursor.execute, query)
            result = await asyncio.to_thread(cursor.fetchone)

            # Turn off XML execution plan
            await asyncio.to_thread(cursor.execute, "SET SHOWPLAN_XML OFF")

            cursor.close()

            return result[0] if result else "<showplan></showplan>"
        except MSSQLError as e:
            raise Exception(f"Failed to get execution plan: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error getting execution plan: {e}")

    async def close(self) -> None:
        """Close the SQL Server connection."""
        if self.connection:
            await asyncio.to_thread(self.connection.close)
            self.connection = None

    def is_connected(self) -> bool:
        """Check if connected to SQL Server."""
        return self.connection is not None
