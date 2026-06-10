"""Minimal JSON-RPC 2.0 handling for the MCP ``tools`` surface.

Implements the subset of the Model Context Protocol needed to expose registry
skills as callable tools: ``initialize``, ``tools/list``, and ``tools/call``.
Each registry skill maps to one MCP tool whose name is the skill name.

Reference: https://modelcontextprotocol.io
"""

from __future__ import annotations

import json
from typing import Any

from skill_registry.errors import SkillNotFoundError
from skill_registry.models import ExecutionStatus
from skill_registry.services import SkillRegistry

PROTOCOL_VERSION = "2025-06-18"

# JSON-RPC error codes.
_PARSE_ERROR = -32700
_INVALID_REQUEST = -32600
_METHOD_NOT_FOUND = -32601
_INVALID_PARAMS = -32602
_INTERNAL_ERROR = -32603


class MCPHandler:
    """Translates JSON-RPC requests into registry calls."""

    def __init__(self, registry: SkillRegistry, server_name: str, server_version: str) -> None:
        self._registry = registry
        self._server_name = server_name
        self._server_version = server_version

    async def handle(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Dispatch a single JSON-RPC request object.

        Returns a response object, or ``None`` for notifications (no ``id``).
        """
        if message.get("jsonrpc") != "2.0" or "method" not in message:
            return self._error(message.get("id"), _INVALID_REQUEST, "invalid JSON-RPC request")

        method = message["method"]
        request_id = message.get("id")
        params = message.get("params") or {}

        # Notifications (no id) require no response.
        is_notification = "id" not in message

        try:
            if method == "initialize":
                result = self._initialize()
            elif method in ("notifications/initialized", "initialized"):
                return None
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = self._tools_list()
            elif method == "tools/call":
                result = await self._tools_call(params)
            else:
                if is_notification:
                    return None
                return self._error(request_id, _METHOD_NOT_FOUND, f"unknown method '{method}'")
        except SkillNotFoundError as exc:
            return self._error(request_id, _INVALID_PARAMS, str(exc))
        except KeyError as exc:
            return self._error(request_id, _INVALID_PARAMS, f"missing parameter: {exc}")
        except Exception as exc:  # noqa: BLE001
            return self._error(request_id, _INTERNAL_ERROR, str(exc))

        if is_notification:
            return None
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    # --- Method implementations -------------------------------------------

    def _initialize(self) -> dict[str, Any]:
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": self._server_name, "version": self._server_version},
        }

    def _tools_list(self) -> dict[str, Any]:
        tools = [
            {
                "name": skill.name,
                "description": skill.manifest.description,
                "inputSchema": skill.manifest.to_mcp_input_schema(),
            }
            for skill in self._registry.list_skills()
        ]
        return {"tools": tools}

    async def _tools_call(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params["name"]
        arguments = params.get("arguments") or {}
        result = await self._registry.execute(name, arguments)

        is_error = result.status is not ExecutionStatus.SUCCESS
        payload = result.error if is_error else json.dumps(result.output, indent=2)
        return {
            "content": [{"type": "text", "text": payload or ""}],
            "isError": is_error,
        }

    # --- Helpers ----------------------------------------------------------

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }

    @property
    def parse_error_code(self) -> int:
        """JSON-RPC parse-error code, for transport-level decode failures."""
        return _PARSE_ERROR
