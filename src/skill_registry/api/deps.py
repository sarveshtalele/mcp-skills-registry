"""FastAPI dependencies.

Singletons (registry, MCP handler) are created once during app startup and stored
on ``app.state``; these helpers expose them to route handlers.
"""

from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, Request, status

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


def require_admin(
    request: Request,
    x_admin_token: str | None = Header(default=None),
) -> None:
    """Guard mutating endpoints with the admin token, when one is configured.

    If ``SKILLREG_ADMIN_TOKEN`` is unset the endpoint is open (logged at startup).
    When set, requests must send a matching ``X-Admin-Token`` header.
    """
    expected = request.app.state.settings.admin_token
    if not expected:
        return
    if not x_admin_token or not hmac.compare_digest(x_admin_token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing or invalid admin token",
        )
