"""Snowflake database driver implementation."""
from typing import List, Dict, Any, Optional, Tuple
from .base import BaseEngine, QueryResult
import asyncio
import time


class SnowflakeEngine(BaseEngine):
    """Snowflake database engine implementation."""

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        ssl: bool = True,
        account: Optional[str] = None,
        warehouse: Optional[str] = None,
        role: Optional[str] = None,
        schema: Optional[str] = None,
        **kwargs
    ):
        """Initialize the Snowflake engine.

        Args:
            host: Snowflake account host (used as fallback for account identifier).
            port: Connection port (default 443 for HTTPS).
            database: Database name.
            username: Snowflake username.
            password: Snowflake password.
            ssl: Use SSL/TLS (always True for Snowflake).
            account: Snowflake account identifier (overrides host if provided).
            warehouse: Virtual warehouse name.
            role: Snowflake role.
            schema: Default schema.
            **kwargs: Additional connection options passed to snowflake.connector.
        """
        self._host = host
        self._port = port
        self._database = database
        self._username = username
        self._password = password
        self._ssl = ssl
        self._account = account or host
        self._warehouse = warehouse
        self._role = role
        self._schema = schema
        self._options = kwargs
        self._connection = None
        self._cursor = None

    async def connect(self) -> None:
        """Establish connection to Snowflake."""
        try:
            import snowflake.connector

            conn_params: Dict[str, Any] = {
                'user': self._username,
                'password': self._password,
                'account': self._account,
                'database': self._database,
            }

            if self._warehouse:
                conn_params['warehouse'] = self._warehouse
            if self._role:
                conn_params['role'] = self._role
            if self._schema:
                conn_params['schema'] = self._schema

            conn_params.update(self._options)

            self._connection = await asyncio.to_thread(
                snowflake.connector.connect, **conn_params
            )
            self._cursor = self._connection.cursor()

        except ImportError:
            raise ImportError(
                "Snowflake connector not installed. "
                "Install with: pip install 'leema-sql[snowflake]'"
            )
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Snowflake: {str(e)}")

    async def execute(self, query: str, params: Optional[Tuple] = None) -> QueryResult:
        """Execute a SQL query and return results."""
        if not self._cursor:
            raise RuntimeError("Not connected to database. Call connect() first.")

        try:
            start_time = time.time()
            if params:
                await asyncio.to_thread(self._cursor.execute, query, params)
            else:
                await asyncio.to_thread(self._cursor.execute, query)

            columns = (
                [desc[0] for desc in self._cursor.description]
                if self._cursor.description else []
            )
            rows = await asyncio.to_thread(self._cursor.fetchall)
            execution_time = time.time() - start_time

            return QueryResult(
                columns=columns,
                rows=list(rows) if rows else [],
                row_count=len(rows) if rows else 0,
                execution_time=execution_time,
            )
        except Exception as e:
            raise RuntimeError(f"Query execution failed: {str(e)}")

    async def get_schema(self) -> Dict[str, List[Dict[str, Any]]]:
        """Retrieve the Snowflake database schema."""
        if not self._cursor:
            raise RuntimeError("Not connected to database. Call connect() first.")

        try:
            await asyncio.to_thread(
                self._cursor.execute,
                "SELECT table_schema, table_name FROM information_schema.tables "
                "WHERE table_type = 'BASE TABLE' ORDER BY table_schema, table_name"
            )
            rows = await asyncio.to_thread(self._cursor.fetchall)

            schema: Dict[str, List[Dict[str, Any]]] = {}
            for table_schema, table_name in rows:
                if table_schema not in schema:
                    schema[table_schema] = []
                schema[table_schema].append({
                    'name': table_name,
                    'columns': []
                })
            return schema
        except Exception as e:
            raise Exception(f"Failed to retrieve schema: {str(e)}")

    async def get_databases(self) -> List[str]:
        """Get list of available databases."""
        if not self._cursor:
            raise RuntimeError("Not connected to database. Call connect() first.")

        try:
            await asyncio.to_thread(self._cursor.execute, "SHOW DATABASES")
            rows = await asyncio.to_thread(self._cursor.fetchall)
            return sorted(row[1] for row in rows)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch databases: {str(e)}")

    async def get_schemas(self, database: str) -> List[str]:
        """Get list of schemas in a database."""
        if not self._cursor:
            raise RuntimeError("Not connected to database. Call connect() first.")

        try:
            await asyncio.to_thread(self._cursor.execute, f"USE DATABASE {database}")
            await asyncio.to_thread(self._cursor.execute, "SHOW SCHEMAS")
            rows = await asyncio.to_thread(self._cursor.fetchall)
            return sorted(row[1] for row in rows)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch schemas: {str(e)}")

    async def get_tables(self, database: str, schema: str) -> List[str]:
        """Get list of tables in a schema."""
        if not self._cursor:
            raise RuntimeError("Not connected to database. Call connect() first.")

        try:
            await asyncio.to_thread(self._cursor.execute, f"USE DATABASE {database}")
            await asyncio.to_thread(self._cursor.execute, f"USE SCHEMA {schema}")
            await asyncio.to_thread(self._cursor.execute, "SHOW TABLES")
            rows = await asyncio.to_thread(self._cursor.fetchall)
            return sorted(row[1] for row in rows)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch tables: {str(e)}")

    async def get_columns(self, database: str, schema: str, table: str) -> List[Dict[str, Any]]:
        """Get column information for a table."""
        if not self._cursor:
            raise RuntimeError("Not connected to database. Call connect() first.")

        try:
            await asyncio.to_thread(
                self._cursor.execute,
                f"DESCRIBE TABLE {database}.{schema}.{table}"
            )
            rows = await asyncio.to_thread(self._cursor.fetchall)

            columns = []
            for row in rows:
                columns.append({
                    'name': row[0],
                    'type': row[1],
                    'nullable': row[3] == 'Y',
                    'default': row[4] if len(row) > 4 else None,
                })
            return columns
        except Exception as e:
            raise RuntimeError(f"Failed to fetch columns: {str(e)}")

    async def get_explain_plan(self, query: str) -> str:
        """Get execution plan for a query."""
        if not self._cursor:
            raise RuntimeError("Not connected to database. Call connect() first.")

        try:
            await asyncio.to_thread(self._cursor.execute, f"EXPLAIN {query}")
            plan_rows = await asyncio.to_thread(self._cursor.fetchall)
            return "\n".join(str(row[0]) for row in plan_rows)
        except Exception as e:
            raise RuntimeError(f"Failed to get execution plan: {str(e)}")

    async def close(self) -> None:
        """Close Snowflake connection."""
        if self._cursor:
            try:
                await asyncio.to_thread(self._cursor.close)
            except Exception:
                pass
            self._cursor = None

        if self._connection:
            try:
                await asyncio.to_thread(self._connection.close)
            except Exception:
                pass
            self._connection = None

    def is_connected(self) -> bool:
        """Check if the connection is alive."""
        return self._connection is not None and self._cursor is not None

