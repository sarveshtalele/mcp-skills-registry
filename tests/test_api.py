"""HTTP-level tests for the REST and MCP surfaces."""

from __future__ import annotations


def test_index(client):
    resp = client.get("/info")
    assert resp.status_code == 200
    assert resp.json()["endpoints"]["mcp"] == "/mcp"


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_list_skills(client):
    resp = client.get("/api/v1/skills")
    assert resp.status_code == 200
    names = [s["name"] for s in resp.json()]
    assert "text-statistics" in names


def test_search_skills(client):
    resp = client.get("/api/v1/skills", params={"q": "readability"})
    assert resp.status_code == 200
    assert any(s["name"] == "text-statistics" for s in resp.json())


def test_get_skill_manifest(client):
    resp = client.get("/api/v1/skills/text-statistics")
    assert resp.status_code == 200
    assert resp.json()["version"] == "1.0.0"


def test_get_unknown_skill_404(client):
    assert client.get("/api/v1/skills/nope").status_code == 404


def test_execute_via_rest(client):
    resp = client.post(
        "/api/v1/skills/text-statistics/execute",
        json={"inputs": {"text": "Hello world. This is a test."}},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert resp.json()["output"]["sentence_count"] == 2


def test_mcp_initialize(client):
    resp = client.post(
        "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    )
    assert resp.status_code == 200
    assert resp.json()["result"]["serverInfo"]["name"]


def test_mcp_tools_list(client):
    resp = client.post("/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tools = resp.json()["result"]["tools"]
    assert any(t["name"] == "text-statistics" for t in tools)


def test_mcp_tools_call(client):
    resp = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "text-statistics", "arguments": {"text": "One. Two."}},
        },
    )
    body = resp.json()["result"]
    assert body["isError"] is False
    assert "word_count" in body["content"][0]["text"]


def test_mcp_notification_returns_202(client):
    resp = client.post("/mcp", json={"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert resp.status_code == 202


def test_download_skill_zip(client):
    resp = client.get("/api/v1/skills/text-statistics/download")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    import io
    import zipfile

    names = zipfile.ZipFile(io.BytesIO(resp.content)).namelist()
    assert any(n.endswith("SKILL.md") for n in names)


def test_download_unknown_skill_404(client):
    assert client.get("/api/v1/skills/nope/download").status_code == 404


def test_list_includes_updated_timestamp(client):
    resp = client.get("/api/v1/skills")
    assert resp.status_code == 200
    assert all("updated" in s for s in resp.json())
