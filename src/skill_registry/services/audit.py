"""Audit service — a thin, fail-safe wrapper over the audit repository."""

from __future__ import annotations

from typing import Any

from skill_registry.logging_config import get_logger
from skill_registry.models import AuditEvent
from skill_registry.repositories import AuditRepository

_logger = get_logger(__name__)


class AuditService:
    """Records audit events. Logging failures never break the request path."""

    def __init__(self, repository: AuditRepository) -> None:
        self._repository = repository

    def record(
        self,
        event_type: str,
        action: str,
        status: str,
        *,
        skill_name: str | None = None,
        user_id: str | None = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Persist an audit event, swallowing storage errors."""
        event = AuditEvent(
            event_type=event_type,
            action=action,
            status=status,
            skill_name=skill_name,
            user_id=user_id,
            error=error,
            metadata=metadata or {},
        )
        try:
            self._repository.append(event)
        except Exception:  # noqa: BLE001 - auditing must not break the caller
            _logger.exception("Failed to write audit event %s/%s", event_type, action)
