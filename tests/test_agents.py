"""Tests for agent discovery, API, and upload."""

from __future__ import annotations

import io
import zipfile


def _agent_zip(name: str = "demo-agent") -> bytes:
    manifest = (
        f"---\nname: {name}\nversion: 1.0.0\n"
        f"description: A demo agent.\nskills: [text-statistics]\n"
        f"workflow:\n  - step: run\n    uses: text-statistics\n    description: do it\n---\n# {name}\n"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(f"{name}/AGENT.md", manifest)
    return buf.getvalue()


def test_list_agents(client):
    resp = client.get("/api/v1/agents")
    assert resp.status_code == 200
    names = [a["name"] for a in resp.json()]
    assert "arch-analyst" in names
    assert "gatekeeper" in names


def test_get_agent(client):
    resp = client.get("/api/v1/agents/migration-eng")
    assert resp.status_code == 200
    assert "task-decomposition" in resp.json()["skills"]


def test_get_unknown_agent_404(client):
    assert client.get("/api/v1/agents/nope").status_code == 404


def test_upload_agent(writable_client, tmp_path, monkeypatch):
    # Point agents dir at a temp location for this client via env is complex;
    # instead validate the upload path returns 201 + manifest.
    resp = writable_client.post(
        "/api/v1/agents/upload",
        files={"file": ("a.zip", _agent_zip("demo-agent"), "application/zip")},
        params={"overwrite": "true"},
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "demo-agent"


def test_validate_agent_coerces_name(writable_client):
    """A non-slug agent name is coerced, not rejected."""
    bad = io.BytesIO()
    with zipfile.ZipFile(bad, "w") as zf:
        zf.writestr("x/AGENT.md", "---\nname: Bad Name!\ndescription: d\n---\n")
    resp = writable_client.post(
        "/api/v1/agents/validate",
        files={"file": ("a.zip", bad.getvalue(), "application/zip")},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "bad-name"


def test_delete_agent(writable_client):
    writable_client.post(
        "/api/v1/agents/upload",
        files={"file": ("a.zip", _agent_zip("temp-agent"), "application/zip")},
        params={"overwrite": "true"},
    )
    assert writable_client.delete("/api/v1/agents/temp-agent").status_code == 204
    assert writable_client.get("/api/v1/agents/temp-agent").status_code == 404
