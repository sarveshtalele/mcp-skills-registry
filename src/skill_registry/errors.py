"""Domain-specific exceptions."""

from __future__ import annotations


class RegistryError(Exception):
    """Base class for all registry errors."""


class SkillNotFoundError(RegistryError):
    """Raised when a requested skill is not registered."""


class ManifestError(RegistryError):
    """Raised when a ``SKILL.md`` cannot be parsed or fails validation."""


class ValidationError(RegistryError):
    """Raised when skill inputs fail validation."""


class ExecutionError(RegistryError):
    """Raised when a skill fails to execute."""
