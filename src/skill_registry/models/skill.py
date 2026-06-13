"""Models describing a skill and its public manifest (``SKILL.md`` frontmatter)."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from skill_registry.models.enums import ExecutionType, SkillStatus

# JSON-Schema primitive types we accept for skill parameters.
ParameterType = Literal["string", "integer", "number", "boolean", "array", "object"]

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


class SkillParameter(BaseModel):
    """A single input or output parameter of a skill."""

    name: str
    type: ParameterType = "string"
    description: str = ""
    required: bool = True
    default: Any | None = None
    enum: list[str] | None = None
    examples: list[Any] | None = None
    # JSON-Schema item type for `array` parameters (defaults to string items).
    items: ParameterType | None = None

    @field_validator("name")
    @classmethod
    def _valid_name(cls, value: str) -> str:
        if not value.isidentifier():
            raise ValueError(f"parameter name '{value}' must be a valid identifier")
        return value


class ExecutionSpec(BaseModel):
    """Describes how the registry should execute the skill."""

    type: ExecutionType = ExecutionType.PYTHON_SCRIPT
    # "scripts/main.py:run" — relative module path and callable name.
    entrypoint: str = "scripts/main.py:run"
    timeout_seconds: int = Field(default=30, ge=1, le=600)

    @field_validator("entrypoint", mode="before")
    @classmethod
    def _coerce_entrypoint(cls, value: object) -> str:
        """Coerce a malformed entrypoint to the default rather than rejecting."""
        text = str(value or "").strip()
        if ":" not in text:
            return "scripts/main.py:run"
        path, _, callable_name = text.partition(":")
        if not path.endswith(".py") or not callable_name.isidentifier():
            return "scripts/main.py:run"
        return text

    @property
    def script_path(self) -> str:
        """Relative path to the entrypoint script."""
        return self.entrypoint.split(":", 1)[0]

    @property
    def callable_name(self) -> str:
        """Name of the entrypoint callable."""
        return self.entrypoint.split(":", 1)[1]


class SkillManifest(BaseModel):
    """Validated representation of a skill's ``SKILL.md`` frontmatter."""

    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = "unknown"
    license: str = "MIT"
    category: str = "general"
    tags: list[str] = Field(default_factory=list)

    execution: ExecutionSpec = Field(default_factory=ExecutionSpec)
    inputs: list[SkillParameter] = Field(default_factory=list)
    outputs: list[SkillParameter] = Field(default_factory=list)

    status: SkillStatus = SkillStatus.ACTIVE
    requires_approval: bool = False
    docs_url: str | None = None
    repository: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def _coerce_name(cls, value: object) -> str:
        """Coerce any name into a safe lowercase slug rather than rejecting it."""
        text = str(value or "").strip().lower()
        slug = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
        return slug or "unnamed-skill"

    @field_validator("version", mode="before")
    @classmethod
    def _coerce_version(cls, value: object) -> str:
        """Accept any version; default to 0.0.0 when it is not semantic."""
        text = str(value or "").strip()
        return text if _SEMVER_RE.match(text) else (text or "0.0.0")

    def to_mcp_input_schema(self) -> dict[str, Any]:
        """Render the inputs as a JSON Schema object for the MCP tool contract."""
        properties: dict[str, Any] = {}
        required: list[str] = []
        for param in self.inputs:
            schema: dict[str, Any] = {"type": param.type, "description": param.description}
            if param.type == "array":
                # JSON Schema requires `items` for arrays; many clients reject it otherwise.
                schema["items"] = {"type": param.items or "string"}
            if param.enum:
                schema["enum"] = param.enum
            if param.default is not None:
                schema["default"] = param.default
            properties[param.name] = schema
            if param.required:
                required.append(param.name)
        return {"type": "object", "properties": properties, "required": required}


class UploadResult(BaseModel):
    """Outcome of an upload: what was installed, where, and any advisories."""

    name: str
    version: str
    kind: str = "skill"  # "skill" or "agent"
    installed_files: list[str] = Field(default_factory=list)
    github_url: str | None = None
    warnings: list[str] = Field(default_factory=list)


class SkillSummary(BaseModel):
    """Lightweight projection used in search and listing responses."""

    name: str
    version: str
    description: str
    category: str
    tags: list[str]
    status: SkillStatus
    relevance: float | None = None
    updated: float | None = None  # epoch seconds of the SKILL.md mtime

    @classmethod
    def from_manifest(
        cls,
        manifest: SkillManifest,
        relevance: float | None = None,
        updated: float | None = None,
    ) -> SkillSummary:
        """Build a summary from a full manifest."""
        return cls(
            name=manifest.name,
            version=manifest.version,
            description=manifest.description,
            category=manifest.category,
            tags=manifest.tags,
            status=manifest.status,
            relevance=relevance,
            updated=updated,
        )
