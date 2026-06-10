"""Tests for the Streamable HTTP MCP transport (sessions, GET, DELETE)."""

from __future__ import annotations

SESSION_HEADER = "mcp-session-id"


def test_initialize_issues_session(client):
    resp = client.post(
        "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    )
    assert resp.status_code == 200
    assert SESSION_HEADER in resp.headers
    assert resp.json()["result"]["protocolVersion"]


def test_request_with_valid_session(client):
    init = client.post(
        "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    )
    session = init.headers[SESSION_HEADER]
    resp = client.post(
        "/mcp",
        headers={"Mcp-Session-Id": session},
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    )
    assert resp.status_code == 200
    assert any(t["name"] == "text-statistics" for t in resp.json()["result"]["tools"])


def test_unknown_session_rejected(client):
    resp = client.post(
        "/mcp",
        headers={"Mcp-Session-Id": "does-not-exist"},
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    )
    assert resp.status_code == 404


def test_get_returns_405(client):
    resp = client.get("/mcp")
    assert resp.status_code == 405
    assert "POST" in resp.headers.get("allow", "")


def test_delete_terminates_session(client):
    init = client.post(
        "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    )
    session = init.headers[SESSION_HEADER]
    assert client.delete("/mcp", headers={"Mcp-Session-Id": session}).status_code == 204
    # Session is gone now.
    again = client.post(
        "/mcp",
        headers={"Mcp-Session-Id": session},
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    )
    assert again.status_code == 404


def test_batch_request(client):
    batch = [
        {"jsonrpc": "2.0", "id": 1, "method": "ping"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    ]
    resp = client.post("/mcp", json=batch)
    assert resp.status_code == 200
    assert len(resp.json()) == 2
