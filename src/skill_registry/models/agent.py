"""Models describing an agent and its public manifest (``AGENT.md`` frontmatter).

An agent orchestrates skills through a workflow. It is a *definition* (not a
server-executed tool): clients load it to drive a multi-step process using the
registry's skills.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


class WorkflowStep(BaseModel):
    """A single step in an agent's workflow."""

    step: str
    uses: str | None = None  # skill name this step invokes, if any
    description: str = ""


class AgentManifest(BaseModel):
    """Validated representation of an ``AGENT.md`` frontmatter block."""

    name: str
    version: str = "1.0.0"
    description: str
    author: str = "unknown"
    license: str = "MIT"
    skills: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    workflow: list[WorkflowStep] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def _valid_name(cls, value: str) -> str:
        if not _SLUG_RE.match(value):
            raise ValueError(f"agent name '{value}' must be a lowercase slug (a-z, 0-9, hyphen)")
        return value

    @field_validator("version")
    @classmethod
    def _valid_version(cls, value: str) -> str:
        if not _SEMVER_RE.match(value):
            raise ValueError(f"version '{value}' must be semantic (MAJOR.MINOR.PATCH)")
        return value


class AgentSummary(BaseModel):
    """Lightweight projection for listing agents."""

    name: str
    version: str
    description: str
    skills: list[str]

    @classmethod
    def from_manifest(cls, manifest: AgentManifest) -> AgentSummary:
        """Build a summary from a full manifest."""
        return cls(
            name=manifest.name,
            version=manifest.version,
            description=manifest.description,
            skills=manifest.skills,
        )
