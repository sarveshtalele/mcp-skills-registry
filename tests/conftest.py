"""Shared pytest fixtures."""

from __future__ import annotations

import io
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from skill_registry.config import Settings
from skill_registry.container import build_container
from skill_registry.services import SkillRegistry

_REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Settings pointing at the repo's real skills dir with an isolated DB."""
    return Settings(
        skills_dir=_REPO_ROOT / "skills",
        agents_dir=_REPO_ROOT / "agents",
        db_path=tmp_path / "test.db",
        enable_ui=False,
    )


@pytest.fixture
def registry(settings: Settings) -> SkillRegistry:
    """A fully wired registry with the catalogue loaded."""
    return build_container(settings).registry


@pytest.fixture
def client(settings: Settings) -> Iterator:
    """A FastAPI TestClient bound to a test app (real skills catalogue)."""
    from fastapi.testclient import TestClient

    from skill_registry.main import create_app

    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def writable_client(tmp_path: Path) -> Iterator:
    """A TestClient backed by an empty, writable temp skills dir (for uploads)."""
    from fastapi.testclient import TestClient

    from skill_registry.main import create_app

    skills_dir = tmp_path / "skills"
    agents_dir = tmp_path / "agents"
    skills_dir.mkdir()
    agents_dir.mkdir()
    settings = Settings(
        skills_dir=skills_dir,
        agents_dir=agents_dir,
        db_path=tmp_path / "test.db",
        enable_ui=False,
    )
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


def make_skill_zip(name: str = "echo-skill", *, nested: bool = True) -> bytes:
    """Build an in-memory ZIP for a minimal valid skill."""
    manifest = (
        f"---\n"
        f"name: {name}\n"
        f"version: 1.0.0\n"
        f"description: Echo the input back.\n"
        f"execution:\n"
        f"  type: python-script\n"
        f"  entrypoint: scripts/main.py:run\n"
        f"inputs:\n"
        f"  - name: value\n"
        f"    type: string\n"
        f"    required: true\n"
        f"    description: text to echo\n"
        f"outputs:\n"
        f"  - name: echoed\n"
        f"    type: string\n"
        f"    description: the echoed text\n"
        f"---\n# {name}\n"
    )
    main_py = "def run(inputs):\n    return {'echoed': inputs['value']}\n"

    prefix = f"{name}/" if nested else ""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{prefix}SKILL.md", manifest)
        zf.writestr(f"{prefix}scripts/main.py", main_py)
    return buffer.getvalue()
