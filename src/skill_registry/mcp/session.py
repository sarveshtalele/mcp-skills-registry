"""In-memory MCP session tracking for the Streamable HTTP transport.

The Streamable HTTP transport assigns a session id at ``initialize`` time and
expects it echoed back on subsequent requests via the ``Mcp-Session-Id`` header.
Sessions here are lightweight (just an id + last-seen timestamp); state lives in
the registry, which is itself stateless per call.
"""

from __future__ import annotations

import time
import uuid
from threading import Lock

_SESSION_TTL_SECONDS = 60 * 60  # 1 hour idle expiry


class SessionManager:
    """Thread-safe registry of active session ids."""

    def __init__(self, ttl_seconds: int = _SESSION_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._sessions: dict[str, float] = {}
        self._lock = Lock()

    def create(self) -> str:
        """Create a new session and return its id."""
        session_id = uuid.uuid4().hex
        with self._lock:
            self._sessions[session_id] = time.monotonic()
        return session_id

    def is_valid(self, session_id: str | None) -> bool:
        """Return True if the session exists and has not expired (refreshes it)."""
        if not session_id:
            return False
        with self._lock:
            created = self._sessions.get(session_id)
            if created is None:
                return False
            if time.monotonic() - created > self._ttl:
                del self._sessions[session_id]
                return False
            self._sessions[session_id] = time.monotonic()
            return True

    def terminate(self, session_id: str | None) -> bool:
        """Remove a session. Returns True if it existed."""
        if not session_id:
            return False
        with self._lock:
            return self._sessions.pop(session_id, None) is not None
