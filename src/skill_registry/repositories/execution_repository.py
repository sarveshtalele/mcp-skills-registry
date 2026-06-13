"""Persistence for execution history."""

from __future__ import annotations

from skill_registry.db import Database
from skill_registry.models import ExecutionResult


class ExecutionRepository:
    """Stores and retrieves skill execution records."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def record(self, result: ExecutionResult, version: str | None, user_id: str | None) -> None:
        """Persist a single execution result."""
        self._db.execute(
            """
            INSERT OR REPLACE INTO executions
                (execution_id, skill_name, version, user_id, status, error, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.execution_id,
                result.skill_name,
                version,
                user_id,
                result.status.value,
                result.error,
                result.duration_ms,
            ),
        )

    def count_for_skill(self, skill_name: str) -> int:
        """Return the total number of executions for a skill."""
        rows = self._db.query(
            "SELECT COUNT(*) AS n FROM executions WHERE skill_name = ?", (skill_name,)
        )
        return int(rows[0]["n"]) if rows else 0

    def counts_by_skill(self) -> dict[str, int]:
        """Return ``{skill_name: execution_count}`` across all skills."""
        rows = self._db.query(
            "SELECT skill_name, COUNT(*) AS n FROM executions GROUP BY skill_name"
        )
        return {r["skill_name"]: int(r["n"]) for r in rows}
