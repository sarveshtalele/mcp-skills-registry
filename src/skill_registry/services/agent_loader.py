"""Discovery and parsing of on-disk agents (``AGENT.md``)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError as PydanticValidationError

from skill_registry.errors import ManifestError
from skill_registry.logging_config import get_logger
from skill_registry.models import AgentManifest
from skill_registry.services.loader import parse_frontmatter

_logger = get_logger(__name__)
_MANIFEST_FILENAME = "AGENT.md"


@dataclass(frozen=True)
class LoadedAgent:
    """A parsed agent with its on-disk location and instructions body."""

    manifest: AgentManifest
    directory: Path
    instructions: str

    @property
    def name(self) -> str:
        """Convenience accessor for the agent name."""
        return self.manifest.name


class AgentLoader:
    """Loads agents from a directory tree."""

    def __init__(self, agents_dir: Path) -> None:
        self._agents_dir = agents_dir

    def load_one(self, manifest_path: Path) -> LoadedAgent:
        """Load and validate a single ``AGENT.md``."""
        data, body = parse_frontmatter(manifest_path.read_text(encoding="utf-8"))
        try:
            manifest = AgentManifest.model_validate(data)
        except PydanticValidationError as exc:
            raise ManifestError(
                f"{manifest_path.parent.name}: agent manifest failed validation: {exc}"
            ) from exc
        return LoadedAgent(manifest=manifest, directory=manifest_path.parent, instructions=body)

    def discover(self) -> dict[str, LoadedAgent]:
        """Scan the agents directory and return a name -> LoadedAgent mapping."""
        agents: dict[str, LoadedAgent] = {}
        if not self._agents_dir.exists():
            _logger.warning("Agents directory %s does not exist", self._agents_dir)
            return agents

        for manifest_path in sorted(self._agents_dir.rglob(_MANIFEST_FILENAME)):
            rel_parts = manifest_path.relative_to(self._agents_dir).parts
            if any(part.startswith("_") for part in rel_parts):
                continue
            try:
                agent = self.load_one(manifest_path)
            except ManifestError as exc:
                _logger.error("Skipping agent at %s: %s", manifest_path.parent, exc)
                continue
            if agent.name in agents:
                _logger.error("Duplicate agent '%s'; keeping first", agent.name)
                continue
            agents[agent.name] = agent
            _logger.info("Loaded agent '%s' v%s", agent.name, agent.manifest.version)

        _logger.info("Discovered %d agent(s)", len(agents))
        return agents
