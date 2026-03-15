"""Abstract base class for database engine drivers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional, Tuple


@dataclass
class QueryResult:
    """Result of a SQL query execution."""
    columns: List[str]
    rows: List[Tuple[Any, ...]]
    row_count: int
    execution_time: float


class BaseEngine(ABC):
    """Abstract base class that all database drivers must implement.

    This ensures a consistent interface across all database engines.
    All methods must be async to support non-blocking UI operations.
    """

    @abstractmethod
    async def connect(self, **kwargs) -> None:
        """Establish a connection to the database.

        Args:
            **kwargs: Connection parameters specific to the database engine.

        Raises:
            ConnectionError: If the connection fails.
        """
        pass

    @abstractmethod
    async def execute(self, query: str, params: Optional[Tuple] = None) -> QueryResult:
        """Execute a SQL query and return the results.

        Args:
            query: The SQL query to execute.
            params: Optional parameters for parameterized queries.

        Returns:
            QueryResult with columns, rows, row count, and execution time.

        Raises:
            RuntimeError: If not connected to the database.
            Exception: For query execution errors.
        """
        pass

    @abstractmethod
    async def get_schema(self) -> Dict[str, List[Dict[str, Any]]]:
        """Retrieve the database schema with lazy loading support.

        Returns:
            Dictionary mapping schema names to lists of table information.
            Each table dict contains 'name' and 'columns' keys.

        Example:
            {
                'public': [
                    {
                        'name': 'users',
                        'columns': [
                            {'name': 'id', 'type': 'INTEGER'},
                            {'name': 'email', 'type': 'VARCHAR'}
                        ]
                    }
                ]
            }
        """
        pass

    @abstractmethod
    async def get_explain_plan(self, query: str) -> str:
        """Get the execution plan for a query.

        Args:
            query: The SQL query to analyze.

        Returns:
            Execution plan as a string (JSON, XML, or text format).
        """
        pass

    @abstractmethod
    async def get_columns(self, database: str, schema: str, table: str) -> List[Dict[str, Any]]:
        """Get columns for a specific table (for lazy loading).

        Args:
            database: The database name.
            schema: The schema name.
            table: The table name.

        Returns:
            List of column dictionaries with 'name' and 'type' keys.
        """
        pass

    @abstractmethod
    async def get_databases(self) -> List[str]:
        """Get list of available databases.

        Returns:
            List of database names.
        """
        pass

    @abstractmethod
    async def get_schemas(self, database: str) -> List[str]:
        """Get list of schemas in a database.

        Args:
            database: The database name.

        Returns:
            List of schema names.
        """
        pass

    @abstractmethod
    async def get_tables(self, database: str, schema: str) -> List[str]:
        """Get list of tables in a schema.

        Args:
            database: The database name.
            schema: The schema name.

        Returns:
            List of table names.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the database connection and clean up resources."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the database connection is active.

        Returns:
            True if connected, False otherwise.
        """
        pass
