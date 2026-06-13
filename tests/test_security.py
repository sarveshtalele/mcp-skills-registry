"""Security-hardening tests: docs gating, admin auth, input cap, env scrubbing."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from skill_registry.config import Settings
from skill_registry.services.executor import _SAFE_ENV_VARS, SkillExecutor

_REPO = Path(__file__).resolve().parent.parent


def _skill_zip(name: str = "sec-skill") -> bytes:
    manifest = (
        f"---\nname: {name}\nversion: 1.0.0\ndescription: d\n"
        "execution:\n  type: python-script\n  entrypoint: scripts/main.py:run\n---\n"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(f"{name}/SKILL.md", manifest)
        zf.writestr(f"{name}/scripts/main.py", "def run(i):\n    return {}\n")
    return buf.getvalue()


# --- Docs gating ---------------------------------------------------------


def test_docs_hidden_by_default(client):
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/docs").status_code == 404


def test_docs_enabled_when_configured(tmp_path):
    from fastapi.testclient import TestClient

    from skill_registry.main import create_app

    settings = Settings(
        skills_dir=_REPO / "skills",
        agents_dir=_REPO / "agents",
        db_path=tmp_path / "d.db",
        enable_ui=False,
        enable_docs=True,
    )
    with TestClient(create_app(settings)) as c:
        assert c.get("/openapi.json").status_code == 200


# --- Admin auth on mutating endpoints ------------------------------------


@pytest.fixture
def admin_client(tmp_path):
    from fastapi.testclient import TestClient

    from skill_registry.main import create_app

    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    skills.mkdir()
    agents.mkdir()
    settings = Settings(
        skills_dir=skills,
        agents_dir=agents,
        db_path=tmp_path / "d.db",
        enable_ui=False,
        admin_token="s3cret",
    )
    with TestClient(create_app(settings)) as c:
        yield c


def test_upload_requires_admin_token(admin_client):
    resp = admin_client.post(
        "/api/v1/skills/upload",
        files={"file": ("s.zip", _skill_zip(), "application/zip")},
    )
    assert resp.status_code == 401


def test_upload_with_admin_token_ok(admin_client):
    resp = admin_client.post(
        "/api/v1/skills/upload",
        files={"file": ("s.zip", _skill_zip(), "application/zip")},
        headers={"X-Admin-Token": "s3cret"},
    )
    assert resp.status_code == 201


def test_delete_requires_admin_token(admin_client):
    assert admin_client.delete("/api/v1/skills/whatever").status_code == 401


# --- Subprocess env scrubbing -------------------------------------------


def test_skill_env_excludes_server_secrets(monkeypatch, settings):
    monkeypatch.setenv("SKILLREG_GITHUB_TOKEN", "super-secret")
    monkeypatch.setenv("JIRA_API_TOKEN", "jira-tok")
    monkeypatch.setenv("PATH", "/usr/bin")
    env = SkillExecutor(settings)._skill_env()
    assert "SKILLREG_GITHUB_TOKEN" not in env  # server secret never exposed
    assert "PATH" in env  # base safe var passes
    assert "JIRA_API_TOKEN" in env  # explicitly allow-listed integration cred
    assert "GITHUB_TOKEN" not in _SAFE_ENV_VARS  # sanity


# --- Input size cap ------------------------------------------------------


async def test_oversized_input_rejected(registry):
    from skill_registry.models import ExecutionStatus

    big = {"text": "x" * 300_000}
    result = await registry.execute("text-statistics", big)
    assert result.status is ExecutionStatus.INVALID_INPUT
