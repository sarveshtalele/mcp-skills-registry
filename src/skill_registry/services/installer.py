"""Install a skill from an uploaded ZIP archive.

Accepts a ZIP whose tree contains a ``SKILL.md`` (at the archive root or one level
down, e.g. ``my-skill/SKILL.md``). The manifest is validated, then the skill's
files are extracted into ``skills/<name>/``.

Security: guards against zip-slip (path traversal), zip bombs (uncompressed-size
cap), absolute/symlink members, and overwriting existing skills unless asked.
"""

from __future__ import annotations

import io
import shutil
import zipfile
from pathlib import Path, PurePosixPath

from skill_registry.config import Settings
from skill_registry.errors import ManifestError, RegistryError
from skill_registry.logging_config import get_logger
from skill_registry.models import SkillManifest
from skill_registry.services.loader import parse_frontmatter

_logger = get_logger(__name__)
_MANIFEST_FILENAME = "SKILL.md"


class InstallError(RegistryError):
    """Raised when an uploaded skill cannot be installed."""


class SkillInstaller:
    """Validates and unpacks uploaded skill archives into the skills directory."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._skills_dir = settings.resolved_skills_dir
        self._agents_dir = settings.resolved_agents_dir

    # --- Agents ----------------------------------------------------------

    def validate_agent_zip(self, data: bytes):
        """Validate an uploaded agent archive (AGENT.md). Returns the manifest."""
        from skill_registry.models import AgentManifest

        if len(data) > self._settings.max_upload_bytes:
            raise InstallError("upload exceeds the maximum allowed size")
        try:
            archive = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile as exc:
            raise InstallError(f"not a valid ZIP archive: {exc}") from exc
        with archive:
            self._check_zip_bomb(archive)
            root = self._find_root(archive, "AGENT.md")
            raw = archive.read(f"{root}AGENT.md").decode("utf-8")
            data_fm, _ = parse_frontmatter(raw)
            try:
                manifest = AgentManifest.model_validate(data_fm)
            except Exception as exc:  # noqa: BLE001
                raise ManifestError(f"uploaded AGENT.md failed validation: {exc}") from exc
            if manifest.name.startswith("_"):
                raise InstallError("agent name must not start with '_'")
        return manifest

    def read_agent_files(self, data: bytes):
        """Return the validated agent manifest and a ``{path: bytes}`` map."""
        manifest = self.validate_agent_zip(data)
        files: dict[str, bytes] = {}
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            root = self._find_root(archive, "AGENT.md")
            for info in archive.infolist():
                if info.is_dir() or not info.filename.startswith(root):
                    continue
                rel = info.filename[len(root) :]
                if not rel:
                    continue
                self._reject_unsafe(rel)
                files[rel] = archive.read(info)
        return manifest, files

    def install_agent_zip(self, data: bytes, *, overwrite: bool = False):
        """Install an agent archive into the agents directory."""
        manifest = self.validate_agent_zip(data)
        target = self._agents_dir / manifest.name
        if target.exists() and not overwrite:
            raise InstallError(
                f"agent '{manifest.name}' already exists (set overwrite=true to replace)"
            )
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            root = self._find_root(archive, "AGENT.md")
            staged = target.with_name(f".{manifest.name}.staging")
            self._extract(archive, root, staged)
        if target.exists():
            shutil.rmtree(target)
        staged.rename(target)
        _logger.info("Installed agent '%s' v%s", manifest.name, manifest.version)
        return manifest

    # --- Skills ----------------------------------------------------------

    def install_zip(self, data: bytes, *, overwrite: bool = False) -> SkillManifest:
        """Install a skill from raw ZIP bytes. Returns the validated manifest."""
        if len(data) > self._settings.max_upload_bytes:
            raise InstallError("upload exceeds the maximum allowed size")
        if not self._settings.enable_uploads:
            raise InstallError("skill uploads are disabled on this server")

        try:
            archive = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile as exc:
            raise InstallError(f"not a valid ZIP archive: {exc}") from exc

        with archive:
            self._check_zip_bomb(archive)
            root = self._find_skill_root(archive)
            manifest = self._read_manifest(archive, root)
            target = self._skills_dir / manifest.name

            if manifest.name.startswith("_"):
                raise InstallError("skill name must not start with '_'")
            if target.exists() and not overwrite:
                raise InstallError(
                    f"skill '{manifest.name}' already exists (set overwrite=true to replace)"
                )

            staged = target.with_name(f".{manifest.name}.staging")
            self._extract(archive, root, staged)
            if target.exists():
                shutil.rmtree(target)
            staged.rename(target)

        _logger.info("Installed skill '%s' v%s", manifest.name, manifest.version)
        return manifest

    def validate_zip(self, data: bytes) -> SkillManifest:
        """Validate an upload without writing anything. Returns the manifest.

        Performs every check ``install_zip`` does (size, archive integrity, bomb
        guard, manifest presence + schema, name rules) but makes no changes.
        """
        if len(data) > self._settings.max_upload_bytes:
            raise InstallError("upload exceeds the maximum allowed size")
        try:
            archive = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile as exc:
            raise InstallError(f"not a valid ZIP archive: {exc}") from exc
        with archive:
            self._check_zip_bomb(archive)
            root = self._find_skill_root(archive)
            manifest = self._read_manifest(archive, root)
            if manifest.name.startswith("_"):
                raise InstallError("skill name must not start with '_'")
        return manifest

    def read_files(self, data: bytes) -> tuple[SkillManifest, dict[str, bytes]]:
        """Return the validated manifest and a ``{relative_path: bytes}`` map.

        Used to publish a skill's files elsewhere (e.g. GitHub) without touching
        the local filesystem. Applies the same safety checks as extraction.
        """
        manifest = self.validate_zip(data)
        files: dict[str, bytes] = {}
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            root = self._find_skill_root(archive)
            for info in archive.infolist():
                if info.is_dir() or not info.filename.startswith(root):
                    continue
                relative = info.filename[len(root) :]
                if not relative:
                    continue
                self._reject_unsafe(relative)
                files[relative] = archive.read(info)
        return manifest, files

    # --- Internals --------------------------------------------------------

    def _check_zip_bomb(self, archive: zipfile.ZipFile) -> None:
        total = sum(info.file_size for info in archive.infolist())
        if total > self._settings.max_uncompressed_bytes:
            raise InstallError("archive uncompressed size exceeds the allowed limit")

    def _find_skill_root(self, archive: zipfile.ZipFile) -> str:
        """Return the in-archive prefix that directly contains SKILL.md."""
        return self._find_root(archive, _MANIFEST_FILENAME)

    @staticmethod
    def _find_root(archive: zipfile.ZipFile, filename: str) -> str:
        """Return the in-archive prefix that directly contains ``filename``."""
        candidates = [name for name in archive.namelist() if PurePosixPath(name).name == filename]
        if not candidates:
            raise InstallError(f"archive does not contain a {filename}")
        chosen = min(candidates, key=lambda n: len(PurePosixPath(n).parts))
        parent = PurePosixPath(chosen).parent
        return "" if str(parent) == "." else f"{parent}/"

    def _read_manifest(self, archive: zipfile.ZipFile, root: str) -> SkillManifest:
        raw = archive.read(f"{root}{_MANIFEST_FILENAME}").decode("utf-8")
        data, _ = parse_frontmatter(raw)
        try:
            return SkillManifest.model_validate(data)
        except Exception as exc:  # noqa: BLE001
            raise ManifestError(f"uploaded SKILL.md failed validation: {exc}") from exc

    def _extract(self, archive: zipfile.ZipFile, root: str, dest: Path) -> None:
        """Extract members under ``root`` into ``dest``, stripping the prefix."""
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        dest_resolved = dest.resolve()

        for info in archive.infolist():
            if info.is_dir() or not info.filename.startswith(root):
                continue
            relative = info.filename[len(root) :]
            if not relative:
                continue
            self._reject_unsafe(relative)

            target = (dest / relative).resolve()
            if not target.is_relative_to(dest_resolved):
                raise InstallError(f"unsafe path in archive: {info.filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)

    @staticmethod
    def _reject_unsafe(relative: str) -> None:
        path = PurePosixPath(relative)
        if path.is_absolute() or ".." in path.parts:
            raise InstallError(f"unsafe path in archive: {relative}")
