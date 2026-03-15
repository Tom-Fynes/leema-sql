"""Database driver registry and factory."""
from typing import Dict, Type
from .base import BaseEngine

# Import all drivers
from .mssql import MSSQLEngine
from .mysql import MySQLEngine
from .postgres import PostgresEngine
from .duckdb import DuckDBEngine
from .trino import TrinoEngine

# Driver registry
DRIVERS: Dict[str, Type[BaseEngine]] = {
    "mssql": MSSQLEngine,
    "mysql": MySQLEngine,
    "postgres": PostgresEngine,
    "duckdb": DuckDBEngine,
    "trino": TrinoEngine,
}

# Optional drivers (fail gracefully if not installed)
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


__all__ = ["BaseEngine", "DRIVERS", "get_engine"]
