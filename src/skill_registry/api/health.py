"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from skill_registry import __version__
from skill_registry.api.deps import get_registry
from skill_registry.services import SkillRegistry

router = APIRouter(tags=["meta"])


@router.get("/info")
async def index(request: Request, registry: SkillRegistry = Depends(get_registry)) -> dict:
    """Service metadata and entry points (the root path serves the upload UI)."""
    endpoints = {
        "mcp": "/mcp",
        "skills": "/api/v1/skills",
        "agents": "/api/v1/agents",
        "upload_ui": "/",
        "health": "/health",
        "info": "/info",
    }
    if request.app.state.settings.enable_docs:
        endpoints["docs"] = "/docs"
    return {
        "name": "MCP Skill Registry",
        "version": __version__,
        "skills_loaded": len(registry.list_skills()),
        "endpoints": endpoints,
    }


@router.get("/health")
async def health(registry: SkillRegistry = Depends(get_registry)) -> dict:
    """Liveness probe with a skill count."""
    return {
        "status": "ok",
        "version": __version__,
        "skills_loaded": len(registry.list_skills()),
    }
