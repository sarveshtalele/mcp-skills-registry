"""Discovery and parsing of on-disk skills.

A skill is any directory under the skills root that contains a ``SKILL.md`` file
with a YAML frontmatter block. The frontmatter is parsed into a
:class:`~skill_registry.models.skill.SkillManifest`; the markdown body (the agent
instructions) is preserved for reference.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import ValidationError as PydanticValidationError

from skill_registry.errors import ManifestError
from skill_registry.logging_config import get_logger
from skill_registry.models import SkillManifest

_logger = get_logger(__name__)

_FRONTMATTER_DELIMITER = "---"
_MANIFEST_FILENAME = "SKILL.md"


@dataclass(frozen=True)
class LoadedSkill:
    """A parsed skill together with its on-disk location and instructions body."""

    manifest: SkillManifest
    directory: Path
    instructions: str

    @property
    def name(self) -> str:
        """Convenience accessor for the skill name."""
        return self.manifest.name

    @property
    def entrypoint_path(self) -> Path:
        """Absolute path to the skill's execution entrypoint script."""
        return self.directory / self.manifest.execution.script_path


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split ``SKILL.md`` text into (frontmatter dict, body).

    Raises:
        ManifestError: if the frontmatter block is missing or malformed.
    """
    stripped = text.lstrip()
    if not stripped.startswith(_FRONTMATTER_DELIMITER):
        raise ManifestError("SKILL.md must begin with a '---' YAML frontmatter block")

    # Drop the opening delimiter, then split on the closing one.
    after_open = stripped[len(_FRONTMATTER_DELIMITER) :]
    closing = after_open.find(f"\n{_FRONTMATTER_DELIMITER}")
    if closing == -1:
        raise ManifestError("SKILL.md frontmatter block is not terminated with '---'")

    raw_yaml = after_open[:closing]
    body = after_open[closing + len(_FRONTMATTER_DELIMITER) + 1 :].lstrip("\n")

    try:
        data = yaml.safe_load(raw_yaml) or {}
    except yaml.YAMLError as exc:
        raise ManifestError(f"invalid YAML in SKILL.md frontmatter: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestError("SKILL.md frontmatter must be a YAML mapping")
    return data, body


class SkillLoader:
    """Loads skills from a directory tree."""

    def __init__(self, skills_dir: Path) -> None:
        self._skills_dir = skills_dir

    def load_one(self, manifest_path: Path) -> LoadedSkill:
        """Load and validate a single ``SKILL.md``."""
        text = manifest_path.read_text(encoding="utf-8")
        data, body = parse_frontmatter(text)
        try:
            manifest = SkillManifest.model_validate(data)
        except PydanticValidationError as exc:
            raise ManifestError(
                f"{manifest_path.parent.name}: manifest failed validation: {exc}"
            ) from exc
        return LoadedSkill(manifest=manifest, directory=manifest_path.parent, instructions=body)

    def discover(self) -> dict[str, LoadedSkill]:
        """Scan the skills directory and return a name -> LoadedSkill mapping.

        Directories whose name starts with ``_`` (e.g. ``_template``) are skipped.
        Skills that fail to load are logged and excluded rather than aborting startup.
        """
        skills: dict[str, LoadedSkill] = {}
        if not self._skills_dir.exists():
            _logger.warning("Skills directory %s does not exist", self._skills_dir)
            return skills

        for manifest_path in sorted(self._skills_dir.glob(f"*/{_MANIFEST_FILENAME}")):
            if manifest_path.parent.name.startswith("_"):
                continue
            try:
                skill = self.load_one(manifest_path)
            except ManifestError as exc:
                _logger.error("Skipping skill at %s: %s", manifest_path.parent, exc)
                continue
            if skill.name in skills:
                _logger.error(
                    "Duplicate skill name '%s' at %s; keeping first",
                    skill.name,
                    manifest_path.parent,
                )
                continue
            skills[skill.name] = skill
            _logger.info("Loaded skill '%s' v%s", skill.name, skill.manifest.version)

        _logger.info("Discovered %d skill(s)", len(skills))
        return skills
