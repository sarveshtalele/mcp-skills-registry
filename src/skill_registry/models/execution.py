"""Models for skill execution requests and results."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    """Terminal status of a skill execution."""

    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    INVALID_INPUT = "invalid_input"
    NOT_FOUND = "not_found"


class ExecutionRequest(BaseModel):
    """Request payload to execute a skill."""

    inputs: dict[str, Any] = Field(default_factory=dict)
    version: str | None = None
    user_id: str | None = None


class ExecutionResult(BaseModel):
    """Outcome of a skill execution."""

    execution_id: str
    skill_name: str
    status: ExecutionStatus
    output: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def succeeded(self) -> bool:
        """True when the execution completed successfully."""
        return self.status is ExecutionStatus.SUCCESS
