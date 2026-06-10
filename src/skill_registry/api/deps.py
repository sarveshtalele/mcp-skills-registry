"""FastAPI dependencies.

Singletons (registry, MCP handler) are created once during app startup and stored
on ``app.state``; these helpers expose them to route handlers.
"""

from __future__ import annotations

from fastapi import Request

from skill_registry.mcp import MCPHandler, SessionManager
from skill_registry.services import SkillRegistry


def get_registry(request: Request) -> SkillRegistry:
    """Return the application's :class:`SkillRegistry`."""
    return request.app.state.registry


def get_mcp_handler(request: Request) -> MCPHandler:
    """Return the application's :class:`MCPHandler`."""
    return request.app.state.mcp_handler


def get_sessions(request: Request) -> SessionManager:
    """Return the application's :class:`SessionManager`."""
    return request.app.state.sessions
