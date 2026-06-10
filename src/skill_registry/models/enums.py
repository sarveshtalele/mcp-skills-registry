"""Enumerations shared across the domain models."""

from __future__ import annotations

from enum import Enum


class SkillStatus(str, Enum):
    """Lifecycle state of a skill."""

    ACTIVE = "active"
    BETA = "beta"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ExecutionType(str, Enum):
    """How a skill is executed."""

    PYTHON_SCRIPT = "python-script"
    PROMPT_BASED = "prompt-based"
