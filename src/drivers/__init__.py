"""Database driver registry and factory."""

from typing import Dict, Type
from .base import BaseEngine, QueryResult

# Driver registry
DRIVERS: Dict[str, Type[BaseEngine]] = {}

# Import drivers gracefully - skip those whose libraries are not installed
try:
    from .mssql import MSSQLEngine

    DRIVERS["mssql"] = MSSQLEngine
except ImportError:
    pass

try:
    from .mysql import MySQLEngine

    DRIVERS["mysql"] = MySQLEngine
except ImportError:
    pass

try:
    from .postgres import PostgresEngine

    DRIVERS["postgres"] = PostgresEngine
except ImportError:
    pass

try:
    from .duckdb import DuckDBEngine

    DRIVERS["duckdb"] = DuckDBEngine
except ImportError:
    pass

try:
    from .trino import TrinoEngine

    DRIVERS["trino"] = TrinoEngine
except ImportError:
    pass

try:
    from .snowflake import SnowflakeEngine

    DRIVERS["snowflake"] = SnowflakeEngine
except ImportError:
    pass


def get_engine(engine_type: str) -> Type[BaseEngine]:
    """Get engine class by type name."""
    if engine_type not in DRIVERS:
        raise ValueError(f"Unknown engine type: {engine_type}")
    return DRIVERS[engine_type]


def get_available_drivers() -> Dict[str, Type[BaseEngine]]:
    """Return a copy of the registered driver map.

    Returns:
        Dictionary mapping engine-type names to their driver classes.
    """
    return dict(DRIVERS)


__all__ = [
    "BaseEngine",
    "QueryResult",
    "DRIVERS",
    "get_engine",
    "get_available_drivers",
]
