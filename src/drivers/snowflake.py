"""Snowflake database driver implementation."""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from .base import BaseEngine, QueryResult


@dataclass
class SnowflakeEngine(BaseEngine):
    """Snowflake database engine implementation."""

    account: Optional[str] = None
    warehouse: Optional[str] = None
    role: Optional[str] = None
    schema: Optional[str] = None

    def __post_init__(self):
        """Initialize Snowflake connection object."""
        super().__post_init__()
        self._cursor = None

    async def connect(self) -> None:
        """Establish connection to Snowflake."""
        try:
            import snowflake.connector

            # Build connection parameters
            conn_params = {
                'user': self.username,
                'password': self.password,
                'account': self.account or self.host,
                'database': self.database,
            }

            # Add optional parameters
            if self.warehouse:
                conn_params['warehouse'] = self.warehouse
            if self.role:
                conn_params['role'] = self.role
            if self.schema:
                conn_params['schema'] = self.schema

            # SSL/TLS settings
            if self.ssl:
                conn_params['protocol'] = 'https'
                conn_params['port'] = self.port or 443

            # Add any additional options
            conn_params.update(self.options)

            self._connection = snowflake.connector.connect(**conn_params)
            self._cursor = self._connection.cursor()

        except ImportError:
            raise ImportError(
                "Snowflake connector not installed. "
                "Install with: pip install 'leema[snowflake]' or pip install snowflake-connector-python"
            )
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Snowflake: {str(e)}")

    async def disconnect(self) -> None:
        """Close Snowflake connection."""
        if self._cursor:
            try:
                self._cursor.close()
            except Exception:
                pass
            self._cursor = None

        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None

    async def execute(self, query: str) -> QueryResult:
        """Execute a SQL query and return results.

        Args:
            query: SQL query string.

        Returns:
            QueryResult with columns, rows, and metadata.
        """
        if not self._cursor:
            raise RuntimeError("Not connected to database")

        import time
        start_time = time.time()

        try:
            self._cursor.execute(query)

            # Get column names
            columns = []
            if self._cursor.description:
                columns = [desc[0] for desc in self._cursor.description]

            # Fetch all rows
            rows = self._cursor.fetchall()

            execution_time = time.time() - start_time

            return QueryResult(
                columns=columns,
                rows=rows,
                row_count=len(rows) if rows else 0,
                execution_time=execution_time
            )

        except Exception as e:
            raise RuntimeError(f"Query execution failed: {str(e)}")

    async def explain(self, query: str) -> str:
        """Get execution plan for a query.

        Args:
            query: SQL query to explain.

        Returns:
            Execution plan as string.
        """
        if not self._cursor:
            raise RuntimeError("Not connected to database")

        try:
            # Snowflake uses EXPLAIN for execution plans
            explain_query = f"EXPLAIN {query}"
            self._cursor.execute(explain_query)

            # Fetch plan rows and format
            plan_rows = self._cursor.fetchall()
            plan_lines = [row[0] for row in plan_rows]

            return "\n".join(plan_lines)

        except Exception as e:
            raise RuntimeError(f"Failed to get execution plan: {str(e)}")

    async def get_databases(self) -> List[str]:
        """Get list of available databases.

        Returns:
            List of database names.
        """
        if not self._cursor:
            raise RuntimeError("Not connected to database")

        try:
            self._cursor.execute("SHOW DATABASES")
            databases = [row[1]
                         # Name is in column 1
                         for row in self._cursor.fetchall()]
            return sorted(databases)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch databases: {str(e)}")

    async def get_schemas(self, database: str) -> List[str]:
        """Get list of schemas in a database.

        Args:
            database: Database name.

        Returns:
            List of schema names.
        """
        if not self._cursor:
            raise RuntimeError("Not connected to database")

        try:
            # Switch to database context
            self._cursor.execute(f"USE DATABASE {database}")

            # Get schemas
            self._cursor.execute("SHOW SCHEMAS")
            schemas = [row[1]
                       # Name is in column 1
                       for row in self._cursor.fetchall()]
            return sorted(schemas)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch schemas: {str(e)}")

    async def get_tables(self, database: str, schema: str) -> List[str]:
        """Get list of tables in a schema.

        Args:
            database: Database name.
            schema: Schema name.

        Returns:
            List of table names.
        """
        if not self._cursor:
            raise RuntimeError("Not connected to database")

        try:
            # Switch context
            self._cursor.execute(f"USE DATABASE {database}")
            self._cursor.execute(f"USE SCHEMA {schema}")

            # Get tables
            self._cursor.execute("SHOW TABLES")
            tables = [row[1]
                      # Name is in column 1
                      for row in self._cursor.fetchall()]
            return sorted(tables)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch tables: {str(e)}")

    async def get_columns(self, database: str, schema: str, table: str) -> List[Dict[str, Any]]:
        """Get column information for a table.

        Args:
            database: Database name.
            schema: Schema name.
            table: Table name.

        Returns:
            List of column dictionaries with name, type, and nullable.
        """
        if not self._cursor:
            raise RuntimeError("Not connected to database")

        try:
            # Use DESCRIBE to get column info
            self._cursor.execute(f"DESCRIBE TABLE {database}.{schema}.{table}")

            columns = []
            for row in self._cursor.fetchall():
                # Snowflake DESCRIBE returns: name, type, kind, null?, default, ...
                columns.append({
                    'name': row[0],
                    'type': row[1],
                    'nullable': row[3] == 'Y',
                    'default': row[4] if len(row) > 4 else None,
                })

            return columns

        except Exception as e:
            raise RuntimeError(f"Failed to fetch columns: {str(e)}")

    def test_connection(self) -> bool:
        """Test if the connection is alive.

        Returns:
            True if connection is active, False otherwise.
        """
        if not self._connection:
            return False

        try:
            self._cursor.execute("SELECT 1")
            return True
        except Exception:
            return False
