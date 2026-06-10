"""Persistence for the audit trail."""

from __future__ import annotations

import json

from skill_registry.db import Database
from skill_registry.models import AuditEvent


class AuditRepository:
    """Append-only store of audit events."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def append(self, event: AuditEvent) -> None:
        """Persist a single audit event."""
        self._db.execute(
            """
            INSERT INTO audit_logs
                (event_type, action, status, skill_name, user_id, error, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_type,
                event.action,
                event.status,
                event.skill_name,
                event.user_id,
                event.error,
                json.dumps(event.metadata),
            ),
        )
