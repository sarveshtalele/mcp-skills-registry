"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from skill_registry import __version__
from skill_registry.api.deps import get_registry
from skill_registry.services import SkillRegistry

router = APIRouter(tags=["meta"])


@router.get("/")
async def index(registry: SkillRegistry = Depends(get_registry)) -> dict:
    """Landing endpoint: service metadata and entry points."""
    return {
        "name": "MCP Skill Registry",
        "version": __version__,
        "skills_loaded": len(registry.list_skills()),
        "endpoints": {
            "mcp": "/mcp",
            "skills": "/api/v1/skills",
            "upload_ui": "/ui",
            "docs": "/docs",
            "health": "/health",
        },
    }


@router.get("/health")
async def health(registry: SkillRegistry = Depends(get_registry)) -> dict:
    """Liveness probe with a skill count."""
    return {
        "status": "ok",
        "version": __version__,
        "skills_loaded": len(registry.list_skills()),
    }
