"""The :class:`SkillRegistry` facade — the application's single entry point.

Holds the in-memory catalogue of loaded skills and coordinates validation,
execution, search, persistence, and auditing.
"""

from __future__ import annotations

from skill_registry.config import Settings
from skill_registry.errors import SkillNotFoundError, ValidationError
from skill_registry.logging_config import get_logger
from skill_registry.models import (
    ExecutionResult,
    ExecutionStatus,
    SkillManifest,
    SkillSummary,
)
from skill_registry.services.audit import AuditService
from skill_registry.services.executor import SkillExecutor
from skill_registry.services.installer import SkillInstaller
from skill_registry.services.loader import LoadedSkill, SkillLoader
from skill_registry.services.search import SearchService
from skill_registry.services.validator import InputValidator

_logger = get_logger(__name__)


class SkillRegistry:
    """Coordinates skill discovery, lookup, search, and execution."""

    def __init__(
        self,
        settings: Settings,
        loader: SkillLoader,
        validator: InputValidator,
        executor: SkillExecutor,
        search: SearchService,
        audit: AuditService,
        installer: SkillInstaller,
        execution_recorder,
    ) -> None:
        self._settings = settings
        self._loader = loader
        self._validator = validator
        self._executor = executor
        self._search = search
        self._audit = audit
        self._installer = installer
        self._record_execution = execution_recorder
        self._skills: dict[str, LoadedSkill] = {}

    # --- Catalogue management ---------------------------------------------

    def reload(self) -> int:
        """(Re)scan the skills directory. Returns the number of skills loaded."""
        self._skills = self._loader.discover()
        self._audit.record("catalogue", "reload", "success", metadata={"count": len(self._skills)})
        return len(self._skills)

    def list_skills(self) -> list[LoadedSkill]:
        """Return all loaded skills."""
        return list(self._skills.values())

    def get(self, name: str) -> LoadedSkill:
        """Return a skill by name or raise :class:`SkillNotFoundError`."""
        try:
            return self._skills[name]
        except KeyError as exc:
            raise SkillNotFoundError(f"skill '{name}' is not registered") from exc

    def get_manifest(self, name: str) -> SkillManifest:
        """Return a skill's manifest."""
        return self.get(name).manifest

    def install_zip(self, data: bytes, *, overwrite: bool = False) -> SkillManifest:
        """Install a skill from an uploaded ZIP archive and refresh the catalogue."""
        manifest = self._installer.install_zip(data, overwrite=overwrite)
        self.reload()
        self._audit.record(
            "catalogue",
            "install",
            "success",
            skill_name=manifest.name,
            metadata={"version": manifest.version},
        )
        return manifest

    # --- Search -----------------------------------------------------------

    def search(
        self,
        query: str | None,
        *,
        category: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[SkillSummary]:
        """Search the catalogue."""
        self._audit.record("discovery", "search", "success", metadata={"query": query or ""})
        return self._search.search(
            query, self._skills.values(), category=category, limit=limit, offset=offset
        )

    # --- Execution --------------------------------------------------------

    async def execute(
        self, name: str, inputs: dict, *, version: str | None = None, user_id: str | None = None
    ) -> ExecutionResult:
        """Validate inputs and execute a skill, recording the outcome."""
        skill = self.get(name)

        try:
            normalised = self._validator.validate(skill.manifest, inputs)
        except ValidationError as exc:
            result = ExecutionResult(
                execution_id="exec_invalid",
                skill_name=name,
                status=ExecutionStatus.INVALID_INPUT,
                error=str(exc),
            )
            self._persist(result, version, user_id)
            return result

        result = await self._executor.execute(skill, normalised)
        self._persist(result, version, user_id)
        return result

    def _persist(self, result: ExecutionResult, version: str | None, user_id: str | None) -> None:
        try:
            self._record_execution(result, version, user_id)
        except Exception:  # noqa: BLE001
            _logger.exception("Failed to persist execution %s", result.execution_id)
        self._audit.record(
            "execution",
            "execute",
            "success" if result.succeeded else "failure",
            skill_name=result.skill_name,
            user_id=user_id,
            error=result.error,
        )
