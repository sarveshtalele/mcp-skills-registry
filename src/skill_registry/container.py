"""Composition root: builds and wires the object graph from settings."""

from __future__ import annotations

from dataclasses import dataclass

from skill_registry.config import Settings
from skill_registry.db import Database
from skill_registry.mcp import MCPHandler, SessionManager
from skill_registry.repositories import AuditRepository, ExecutionRepository
from skill_registry.services import (
    AuditService,
    InputValidator,
    SearchService,
    SkillExecutor,
    SkillInstaller,
    SkillLoader,
    SkillRegistry,
)


@dataclass
class Container:
    """Holds the fully wired application singletons."""

    settings: Settings
    registry: SkillRegistry
    mcp_handler: MCPHandler
    sessions: SessionManager


def build_container(settings: Settings) -> Container:
    """Construct the registry and MCP handler from configuration."""
    database = Database(settings.resolved_db_path)
    audit = AuditService(AuditRepository(database))
    execution_repo = ExecutionRepository(database)

    registry = SkillRegistry(
        settings=settings,
        loader=SkillLoader(settings.resolved_skills_dir),
        validator=InputValidator(),
        executor=SkillExecutor(settings),
        search=SearchService(settings),
        audit=audit,
        installer=SkillInstaller(settings),
        execution_recorder=execution_repo.record,
    )
    registry.reload()

    handler = MCPHandler(registry, settings.title, settings.version)
    return Container(
        settings=settings,
        registry=registry,
        mcp_handler=handler,
        sessions=SessionManager(),
    )
