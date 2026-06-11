"""Publish a skill's files to the GitHub repository's ``skills/`` folder.

Uses the GitHub Git Data API to create a single commit containing all of the
skill's files under ``skills/<name>/``. Pushing to the default branch triggers
the repository's deploy workflow, which redeploys the Hugging Face Space.

Requires a token with ``repo`` (contents write) scope, supplied via settings.
Uses only the standard library (``urllib``) — no extra dependencies.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Any

from skill_registry.config import Settings
from skill_registry.errors import RegistryError
from skill_registry.logging_config import get_logger

_logger = get_logger(__name__)
_API = "https://api.github.com"


class PublishError(RegistryError):
    """Raised when publishing to GitHub fails."""


class GitHubPublisher:
    """Commits skill files to the GitHub repository via the Git Data API."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def enabled(self) -> bool:
        """True when a token + repo are configured."""
        return self._settings.github_publish_enabled

    def publish_skill(self, name: str, files: dict[str, bytes]) -> str:
        """Commit ``files`` under ``skills/<name>/``. Returns the commit URL."""
        return self._publish("skills", name, files)

    def publish_agent(self, name: str, files: dict[str, bytes]) -> str:
        """Commit ``files`` under ``agents/<name>/``. Returns the commit URL."""
        return self._publish("agents", name, files)

    def _publish(self, folder: str, name: str, files: dict[str, bytes]) -> str:
        if not self.enabled:
            raise PublishError("GitHub publishing is not configured (no token)")

        branch = self._settings.github_branch
        ref = self._get(f"/git/ref/heads/{branch}")
        base_commit_sha = ref["object"]["sha"]
        base_commit = self._get(f"/git/commits/{base_commit_sha}")
        base_tree_sha = base_commit["tree"]["sha"]

        tree_entries = []
        for rel_path, content in files.items():
            blob = self._post(
                "/git/blobs",
                {"content": base64.b64encode(content).decode("ascii"), "encoding": "base64"},
            )
            tree_entries.append(
                {
                    "path": f"{folder}/{name}/{rel_path}",
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob["sha"],
                }
            )

        new_tree = self._post("/git/trees", {"base_tree": base_tree_sha, "tree": tree_entries})
        commit = self._post(
            "/git/commits",
            {
                "message": f"Add/update {folder[:-1]} '{name}' via upload UI",
                "tree": new_tree["sha"],
                "parents": [base_commit_sha],
            },
        )
        self._patch(f"/git/refs/heads/{branch}", {"sha": commit["sha"]})
        _logger.info("Published skill '%s' to GitHub (%s)", name, commit["sha"][:8])
        return commit.get("html_url", "")

    # --- HTTP helpers -----------------------------------------------------

    def _request(self, method: str, path: str, body: dict | None = None) -> dict[str, Any]:
        url = f"{_API}/repos/{self._settings.github_repo}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self._settings.github_token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("User-Agent", "mcp-skill-registry")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            raise PublishError(f"GitHub API {method} {path} failed: {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise PublishError(f"GitHub API request failed: {exc.reason}") from exc

    def _get(self, path: str) -> dict[str, Any]:
        return self._request("GET", path)

    def _post(self, path: str, body: dict) -> dict[str, Any]:
        return self._request("POST", path, body)

    def _patch(self, path: str, body: dict) -> dict[str, Any]:
        return self._request("PATCH", path, body)
