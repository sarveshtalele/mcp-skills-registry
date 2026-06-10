"""Thin SQLite wrapper with connection-per-call semantics.

SQLite connections are not safe to share across threads, so each operation opens
its own short-lived connection. This is more than adequate for the registry's
modest write volume (execution + audit logging).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from skill_registry.logging_config import get_logger

_logger = get_logger(__name__)
_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


class Database:
    """Manages SQLite access for the registry's runtime tables."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self):
        """Yield a configured connection that commits on success and always closes."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        schema = _SCHEMA_PATH.read_text(encoding="utf-8")
        with self._connect() as conn:
            conn.executescript(schema)
        _logger.info("Database initialised at %s", self._db_path)

    def execute(self, query: str, params: Iterable[Any] = ()) -> None:
        """Run a write statement."""
        with self._connect() as conn:
            conn.execute(query, tuple(params))

    def query(self, query: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        """Run a read statement and return all rows."""
        with self._connect() as conn:
            return conn.execute(query, tuple(params)).fetchall()
