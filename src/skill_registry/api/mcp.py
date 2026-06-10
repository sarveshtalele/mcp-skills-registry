"""MCP Streamable HTTP transport (2025-03-26 / 2025-06-18 spec).

A single ``/mcp`` endpoint serves three methods:

- ``POST``   — submit JSON-RPC request(s); responses returned as ``application/json``.
- ``GET``    — open the server→client stream. This server pushes nothing, so it
  returns ``405`` (spec-permitted), which compliant clients handle gracefully.
- ``DELETE`` — terminate the session.

A session id is issued on ``initialize`` and returned via the ``Mcp-Session-Id``
header; clients echo it on later requests. Validation is lenient: an *unknown*
session id is rejected (404), but requests without one are still accepted so the
endpoint also works for simple stateless callers.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, Request, Response

from skill_registry.api.deps import get_mcp_handler, get_sessions
from skill_registry.mcp import MCPHandler, SessionManager

router = APIRouter(tags=["mcp"])

SESSION_HEADER = "Mcp-Session-Id"
PROTOCOL_HEADER = "Mcp-Protocol-Version"
_JSON = "application/json"


def _is_initialize(payload: Any) -> bool:
    messages = payload if isinstance(payload, list) else [payload]
    return any(isinstance(m, dict) and m.get("method") == "initialize" for m in messages)


@router.post("/mcp")
async def mcp_post(
    request: Request,
    handler: MCPHandler = Depends(get_mcp_handler),
    sessions: SessionManager = Depends(get_sessions),
) -> Response:
    """Handle a JSON-RPC request, batch, or notification."""
    raw = await request.body()
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return _error_response(None, handler.parse_error_code, "parse error", 400)

    incoming_session = request.headers.get(SESSION_HEADER)
    initializing = _is_initialize(payload)

    # Reject a stale/unknown session id (unless this is a fresh initialize).
    if incoming_session and not initializing and not sessions.is_valid(incoming_session):
        return _error_response(None, handler.parse_error_code, "invalid or expired session", 404)

    headers: dict[str, str] = {}
    if initializing:
        headers[SESSION_HEADER] = sessions.create()

    if isinstance(payload, list):
        responses = [r for item in payload if (r := await handler.handle(item)) is not None]
        body: Any = responses if responses else None
    else:
        body = await handler.handle(payload)

    if body is None:  # only notifications/responses — nothing to return
        return Response(status_code=202, headers=headers)
    return Response(json.dumps(body), media_type=_JSON, headers=headers)


@router.get("/mcp")
async def mcp_get() -> Response:
    """No server-initiated stream is offered; signal this per spec."""
    return Response(status_code=405, headers={"Allow": "POST, DELETE"})


@router.delete("/mcp")
async def mcp_delete(
    request: Request, sessions: SessionManager = Depends(get_sessions)
) -> Response:
    """Terminate the session identified by the ``Mcp-Session-Id`` header."""
    session_id = request.headers.get(SESSION_HEADER)
    if sessions.terminate(session_id):
        return Response(status_code=204)
    return Response(status_code=404)


def _error_response(request_id: Any, code: int, message: str, status: int) -> Response:
    body = {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
    return Response(json.dumps(body), media_type=_JSON, status_code=status)
