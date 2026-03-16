"""Trino (formerly Presto SQL) database driver implementation."""

try:
    from trino.dbapi import connect
    from trino.auth import BasicAuthentication, CertificateAuthentication
    from trino.exceptions import TrinoUserError, TrinoQueryError
except ImportError:
    raise ImportError(
        "trino is not installed. Install with: pip install 'leema-sql[trino]'"
    )

from typing import List, Dict, Any, Optional, Tuple
from src.drivers.base import BaseEngine, QueryResult
import asyncio
import time


class TrinoEngine(BaseEngine):
    """Trino engine implementation using trino-python-client.

    Trino is designed for distributed SQL queries across multiple data sources.
    Note: trino client is synchronous, so we wrap calls in asyncio.to_thread.
    """

    def __init__(
        self,
        host: str,
        port: int,
        catalog: str = "",
        schema: str = "default",
        username: str = "",
        database: str = "",
        http_scheme: str = "http",
        **kwargs,
    ):
        """Initialize the Trino engine.

        Args:
            host: Trino coordinator host.
            port: Trino coordinator port (default 8080).
            catalog: Catalog name (e.g., 'hive', 'postgresql').  When omitted
                Trino will use its own default catalog.
            schema: Default schema name.  Defaults to ``"default"``.
            username: Username.  May be omitted for Trino clusters that do not
                require authentication.
            database: Alias for *catalog*.  Used by the generic engine factory
                in ``app.py`` which passes ``database=`` for all engines.
                *catalog* takes priority when both are supplied.
            http_scheme: ``'http'`` or ``'https'``.  Setting ``ssl=True`` in
                **kwargs** will automatically upgrade this to ``'https'``.
            **kwargs: Additional connection parameters forwarded to the trino
                client (e.g., ``verify``, ``request_timeout``).  The following
                special keys are consumed here and not forwarded:

                * ``password`` – converted to a
                  :class:`~trino.auth.BasicAuthentication` object.
                * ``ssl`` – ``True`` upgrades *http_scheme* to ``'https'``.
                * ``cert_path`` / ``key_path`` – converted to a
                  :class:`~trino.auth.CertificateAuthentication` object.
                  Certificate auth takes priority over password auth.
        """
        # 'database' is accepted as an alias for 'catalog' so that the generic
        # engine factory in app.py (which always passes database=...) works for
        # Trino without requiring a Trino-specific code path there.
        resolved_catalog = catalog or database

        # Handle password → BasicAuthentication
        password = kwargs.pop("password", None)

        # Handle ssl flag → upgrade http_scheme to https
        ssl = kwargs.pop("ssl", False)
        if ssl and http_scheme == "http":
            http_scheme = "https"

        # Handle certificate-based authentication
        cert_path = kwargs.pop("cert_path", None)
        key_path = kwargs.pop("key_path", None)

        self.connection_params: Dict[str, Any] = {
            "host": host,
            "port": port,
            "user": username,
            "http_scheme": http_scheme,
        }

        if resolved_catalog:
            self.connection_params["catalog"] = resolved_catalog

        if schema:
            self.connection_params["schema"] = schema

        # Certificate auth takes priority over password auth
        if cert_path and key_path:
            self.connection_params["auth"] = CertificateAuthentication(
                cert_path, key_path
            )
        elif password:
            self.connection_params["auth"] = BasicAuthentication(username, password)

        # Pass remaining kwargs (e.g., verify) directly to the trino client
        self.connection_params.update(kwargs)

        self.connection = None
        self.catalog = resolved_catalog
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

    async def execute(self, query: str, params: Optional[Tuple] = None) -> QueryResult:
        """Execute a SQL query."""
        if not self.connection:
            raise RuntimeError("Not connected to database. Call connect() first.")

        try:
            start_time = time.time()
            cursor = self.connection.cursor()

            # Execute in thread pool to avoid blocking
            if params:
                await asyncio.to_thread(cursor.execute, query, params)
            else:
                await asyncio.to_thread(cursor.execute, query)

            # Fetch results
            rows = await asyncio.to_thread(cursor.fetchall)
            columns = (
                [desc[0] for desc in cursor.description] if cursor.description else []
            )
            cursor.close()

            execution_time = time.time() - start_time
            return QueryResult(
                columns=columns,
                rows=list(rows),
                row_count=len(rows),
                execution_time=execution_time,
            )
        except (TrinoUserError, TrinoQueryError) as e:
            raise Exception(f"Query execution failed: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error during query execution: {e}")

    async def get_schema(self) -> Dict[str, List[Dict[str, Any]]]:
        """Retrieve the Trino catalog schema."""
        if not self.connection:
            raise RuntimeError("Not connected to database. Call connect() first.")

        query = f"""
        SELECT table_schema, table_name
        FROM "{self.catalog}".information_schema.tables
        WHERE table_catalog = ?
        ORDER BY table_schema, table_name
        """

        try:
            cursor = self.connection.cursor()
            await asyncio.to_thread(cursor.execute, query, [self.catalog])
            rows = await asyncio.to_thread(cursor.fetchall)
            cursor.close()

            schema: Dict[str, List[Dict[str, Any]]] = {}
            for table_schema, table_name in rows:
                if table_schema not in schema:
                    schema[table_schema] = []

                schema[table_schema].append(
                    {
                        "name": table_name,
                        "columns": [],  # Will be loaded lazily
                    }
                )

            return schema
        except (TrinoUserError, TrinoQueryError) as e:
            raise Exception(f"Failed to retrieve schema: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error retrieving schema: {e}")

    async def get_databases(self) -> List[str]:
        """Get list of available catalogs in Trino."""
        if not self.connection:
            raise RuntimeError("Not connected to database. Call connect() first.")

        try:
            cursor = self.connection.cursor()
            await asyncio.to_thread(cursor.execute, "SHOW CATALOGS")
            rows = await asyncio.to_thread(cursor.fetchall)
            cursor.close()
            return [row[0] for row in rows]
        except Exception as e:
            raise Exception(f"Failed to retrieve databases: {e}")

    async def get_schemas(self, database: str) -> List[str]:
        """Get list of schemas in a catalog."""
        if not self.connection:
            raise RuntimeError("Not connected to database. Call connect() first.")

        try:
            cursor = self.connection.cursor()
            await asyncio.to_thread(cursor.execute, f'SHOW SCHEMAS FROM "{database}"')
            rows = await asyncio.to_thread(cursor.fetchall)
            cursor.close()
            return [row[0] for row in rows]
        except Exception as e:
            raise Exception(f"Failed to retrieve schemas: {e}")

    async def get_tables(self, database: str, schema: str) -> List[str]:
        """Get list of tables in a schema."""
        if not self.connection:
            raise RuntimeError("Not connected to database. Call connect() first.")

        try:
            cursor = self.connection.cursor()
            await asyncio.to_thread(
                cursor.execute, f'SHOW TABLES FROM "{database}"."{schema}"'
            )
            rows = await asyncio.to_thread(cursor.fetchall)
            cursor.close()
            return [row[0] for row in rows]
        except Exception as e:
            raise Exception(f"Failed to retrieve tables: {e}")

    async def get_columns(
        self, database: str, schema: str, table: str
    ) -> List[Dict[str, Any]]:
        """Get columns for a specific table."""
        if not self.connection:
            raise RuntimeError("Not connected to database. Call connect() first.")

        query = f"""
        SELECT column_name, data_type
        FROM "{database}".information_schema.columns
        WHERE table_schema = ? AND table_name = ?
        ORDER BY ordinal_position
        """

        try:
            cursor = self.connection.cursor()
            await asyncio.to_thread(cursor.execute, query, [schema, table])
            rows = await asyncio.to_thread(cursor.fetchall)
            cursor.close()

            return [{"name": col[0], "type": col[1]} for col in rows]
        except (TrinoUserError, TrinoQueryError) as e:
            raise Exception(f"Failed to retrieve columns: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error retrieving columns: {e}")

    async def get_explain_plan(self, query: str) -> str:
        """Get the execution plan in text format."""
        if not self.connection:
            raise RuntimeError("Not connected to database. Call connect() first.")

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
