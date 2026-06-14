"""
SQLite connection manager with context manager support.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from app.config import settings
from app.utils.logger import get_db_logger

logger = get_db_logger()


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Get a new SQLite connection with optimized settings."""
    path = db_path or settings.database.path
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(f"PRAGMA journal_mode={settings.database.journal_mode}")
    return conn


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database connections with auto-commit/rollback."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error (rolled back): {e}")
        raise
    finally:
        conn.close()


@contextmanager
def get_cursor() -> Generator[sqlite3.Cursor, None, None]:
    """Context manager that yields a cursor and handles commit/rollback."""
    with get_db() as conn:
        cursor = conn.cursor()
        yield cursor
