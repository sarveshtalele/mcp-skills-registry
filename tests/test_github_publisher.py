"""Tests for the GitHub publisher (HTTP layer mocked)."""

from __future__ import annotations

from unittest.mock import patch

from skill_registry.config import Settings
from skill_registry.services import GitHubPublisher, PublishError


def _settings(**kw) -> Settings:
    return Settings(github_token=kw.get("token", ""), github_repo="owner/repo")


def test_disabled_without_token():
    pub = GitHubPublisher(_settings(token=""))
    assert pub.enabled is False
    try:
        pub.publish_skill("x", {"SKILL.md": b"---\nname: x\n---\n"})
        raise AssertionError("expected PublishError")
    except PublishError:
        pass


def test_publish_sequences_git_data_api():
    pub = GitHubPublisher(_settings(token="ghp_test"))
    assert pub.enabled is True

    calls: list[tuple[str, str]] = []

    def fake_request(method, path, body=None):
        calls.append((method, path))
        if path.startswith("/git/ref/heads/"):
            return {"object": {"sha": "base"}}
        if path.startswith("/git/commits/"):
            return {"tree": {"sha": "basetree"}}
        if path == "/git/blobs":
            return {"sha": "blob1"}
        if path == "/git/trees":
            return {"sha": "newtree"}
        if path == "/git/commits":
            return {"sha": "newcommit", "html_url": "https://github.com/owner/repo/commit/x"}
        if path.startswith("/git/refs/heads/"):
            return {}
        raise AssertionError(f"unexpected {method} {path}")

    with patch.object(GitHubPublisher, "_request", side_effect=fake_request):
        url = pub.publish_skill("demo", {"SKILL.md": b"x", "scripts/main.py": b"y"})

    assert url == "https://github.com/owner/repo/commit/x"
    methods = [m for m, _ in calls]
    assert methods.count("POST") >= 4  # 2 blobs + tree + commit
    assert ("PATCH", "/git/refs/heads/main") in calls


def test_files_roundtrip_through_installer(settings):
    """read_files returns the manifest and every file as bytes."""
    import io
    import zipfile

    from skill_registry.services import SkillInstaller

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("demo/SKILL.md", "---\nname: demo\ndescription: d\n---\n")
        zf.writestr("demo/scripts/main.py", "def run(i):\n    return {}\n")
    manifest, files = SkillInstaller(settings).read_files(buf.getvalue())
    assert manifest.name == "demo"
    assert set(files) == {"SKILL.md", "scripts/main.py"}
