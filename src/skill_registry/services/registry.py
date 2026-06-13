"""The :class:`SkillRegistry` facade — the application's single entry point.

Holds the in-memory catalogue of loaded skills and coordinates validation,
execution, search, persistence, and auditing.
"""

from __future__ import annotations

import io
import json
import shutil
import zipfile

from skill_registry.config import Settings
from skill_registry.errors import SkillNotFoundError, ValidationError
from skill_registry.logging_config import get_logger
from skill_registry.models import (
    ExecutionResult,
    ExecutionStatus,
    SkillManifest,
    SkillSummary,
    UploadResult,
)
from skill_registry.services.agent_loader import AgentLoader, LoadedAgent
from skill_registry.services.audit import AuditService
from skill_registry.services.executor import SkillExecutor
from skill_registry.services.github_publisher import GitHubPublisher
from skill_registry.services.installer import SkillInstaller
from skill_registry.services.loader import LoadedSkill, SkillLoader
from skill_registry.services.search import SearchService
from skill_registry.services.validator import InputValidator

_logger = get_logger(__name__)


def _skill_warnings(manifest, files: dict) -> list[str]:
    """Non-blocking advisories shown to the uploader (never reject the upload)."""
    warnings: list[str] = []
    if "SKILL.md" not in files:
        warnings.append("SKILL.md not found at the skill root after extraction")
    if manifest.execution.type.value == "python-script":
        if manifest.execution.script_path not in files:
            warnings.append(
                f"entrypoint '{manifest.execution.script_path}' not present — "
                "the skill will load but cannot execute until added"
            )
    if not manifest.description:
        warnings.append("no description provided")
    return warnings


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
        publisher: GitHubPublisher,
        agent_loader: AgentLoader,
        execution_repo,
        audit_repo,
    ) -> None:
        self._settings = settings
        self._loader = loader
        self._agent_loader = agent_loader
        self._validator = validator
        self._executor = executor
        self._search = search
        self._audit = audit
        self._installer = installer
        self._publisher = publisher
        self._execution_repo = execution_repo
        self._audit_repo = audit_repo
        self._record_execution = execution_repo.record
        self._skills: dict[str, LoadedSkill] = {}
        self._agents: dict[str, LoadedAgent] = {}

    # --- Metrics ----------------------------------------------------------

    def record_download(self, name: str) -> None:
        """Log a skill download (for download counts)."""
        self._audit.record("download", "download", "success", skill_name=name)

    def stats(self) -> dict:
        """Aggregate registry metrics for the dashboard."""
        runs = self._execution_repo.counts_by_skill()
        downloads = self._audit_repo.counts_by_skill("download")
        names = [s.name for s in self.list_skills()]
        per_skill = [
            {"name": n, "runs": runs.get(n, 0), "downloads": downloads.get(n, 0)} for n in names
        ]
        per_skill.sort(key=lambda s: (s["downloads"] + s["runs"]), reverse=True)
        categories: dict[str, int] = {}
        for s in self.list_skills():
            categories[s.manifest.category] = categories.get(s.manifest.category, 0) + 1
        return {
            "skills": len(names),
            "agents": len(self._agents),
            "categories": len(categories),
            "total_runs": sum(runs.values()),
            "total_downloads": sum(downloads.values()),
            "category_breakdown": categories,
            "popular": per_skill[:6],
            "per_skill": {s["name"]: s for s in per_skill},
        }

    # --- Catalogue management ---------------------------------------------

    def reload(self) -> int:
        """(Re)scan the skills and agents directories. Returns the skill count."""
        self._skills = self._loader.discover()
        self._agents = self._agent_loader.discover()
        self._audit.record(
            "catalogue",
            "reload",
            "success",
            metadata={"skills": len(self._skills), "agents": len(self._agents)},
        )
        return len(self._skills)

    # --- Agents -----------------------------------------------------------

    def list_agents(self) -> list[LoadedAgent]:
        """Return all loaded agents."""
        return list(self._agents.values())

    def get_agent(self, name: str) -> LoadedAgent:
        """Return an agent by name or raise :class:`SkillNotFoundError`."""
        try:
            return self._agents[name]
        except KeyError as exc:
            raise SkillNotFoundError(f"agent '{name}' is not registered") from exc

    def install_and_publish_agent(self, data: bytes, *, overwrite: bool = False) -> UploadResult:
        """Validate, install, and (if configured) commit an agent to GitHub."""
        manifest, files = self._installer.read_agent_files(data)
        self._installer.install_agent_zip(data, overwrite=overwrite)
        self.reload()
        github_url: str | None = None
        if self._publisher.enabled:
            github_url = self._publisher.publish_agent(manifest.name, files)
        self._audit.record(
            "catalogue",
            "publish_agent",
            "success",
            skill_name=manifest.name,
            metadata={"github": bool(github_url)},
        )
        warnings = [] if "AGENT.md" in files else ["AGENT.md not found at the expected location"]
        return UploadResult(
            name=manifest.name,
            version=manifest.version,
            kind="agent",
            installed_files=sorted(files),
            github_url=github_url,
            warnings=warnings,
        )

    def delete_agent(self, name: str) -> None:
        """Remove an agent from disk and refresh the catalogue."""
        agent = self.get_agent(name)
        self._safe_rmtree(agent.directory, self._settings.resolved_agents_dir)
        self.reload()
        self._audit.record("catalogue", "delete_agent", "success", skill_name=name)

    @staticmethod
    def _safe_rmtree(target, root) -> None:
        """Delete ``target`` only if it is inside ``root`` (guards traversal)."""
        target = target.resolve()
        root = root.resolve()
        if target == root or root not in target.parents:
            raise SkillNotFoundError("refusing to delete outside the managed directory")
        shutil.rmtree(target)

    def validate_agent_upload(self, data: bytes):
        """Validate an uploaded agent ZIP without installing it."""
        return self._installer.validate_agent_zip(data)

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

    def validate_upload(self, data: bytes) -> SkillManifest:
        """Validate an uploaded ZIP without installing it."""
        return self._installer.validate_zip(data)

    def publish_enabled(self) -> bool:
        """True when GitHub auto-publish is configured."""
        return self._publisher.enabled

    def install_and_publish(self, data: bytes, *, overwrite: bool = False) -> UploadResult:
        """Validate, install locally, and (if configured) commit a skill to GitHub."""
        manifest, files = self._installer.read_files(data)
        self._installer.install_zip(data, overwrite=overwrite)
        self.reload()

        github_url: str | None = None
        if self._publisher.enabled:
            github_url = self._publisher.publish_skill(manifest.name, files)

        self._audit.record(
            "catalogue",
            "publish",
            "success",
            skill_name=manifest.name,
            metadata={"version": manifest.version, "github": bool(github_url)},
        )
        return UploadResult(
            name=manifest.name,
            version=manifest.version,
            kind="skill",
            installed_files=sorted(files),
            github_url=github_url,
            warnings=_skill_warnings(manifest, files),
        )

    def package_skill(self, name: str) -> bytes:
        """Return the skill's folder as a ZIP archive (``<name>/...`` layout)."""
        skill = self.get(name)
        root = skill.directory
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(root.rglob("*")):
                if path.is_dir() or "__pycache__" in path.parts or path.suffix == ".pyc":
                    continue
                zf.write(path, arcname=f"{name}/{path.relative_to(root)}")
        return buffer.getvalue()

    def delete_skill(self, name: str) -> None:
        """Remove a skill from disk and refresh the catalogue."""
        skill = self.get(name)
        self._safe_rmtree(skill.directory, self._settings.resolved_skills_dir)
        self.reload()
        self._audit.record("catalogue", "delete", "success", skill_name=name)

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

        # Reject oversized input payloads before doing any work.
        if len(json.dumps(inputs, default=str)) > self._settings.max_input_bytes:
            result = ExecutionResult(
                execution_id="exec_invalid",
                skill_name=name,
                status=ExecutionStatus.INVALID_INPUT,
                error="input payload exceeds the maximum allowed size",
            )
            self._persist(result, version, user_id)
            return result

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
