"""Create a Jira issue via the Jira Cloud REST API (stdlib only)."""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request


def run(inputs: dict) -> dict:
    base = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    email = os.getenv("JIRA_EMAIL", "")
    token = os.getenv("JIRA_API_TOKEN", "")
    if not (base and email and token):
        raise RuntimeError(
            "Jira is not configured. Set JIRA_BASE_URL, JIRA_EMAIL, and "
            "JIRA_API_TOKEN environment variables on the server."
        )

    payload = {
        "fields": {
            "project": {"key": inputs["project_key"]},
            "summary": inputs["summary"],
            "issuetype": {"name": inputs.get("issue_type") or "Task"},
            "description": inputs.get("description") or "",
        }
    }
    data = json.dumps(payload).encode("utf-8")
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    req = urllib.request.Request(f"{base}/rest/api/2/issue", data=data, method="POST")
    req.add_header("Authorization", f"Basic {auth}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"Jira API error {exc.code}: {detail}") from exc

    key = body.get("key", "")
    return {"key": key, "url": f"{base}/browse/{key}" if key else ""}
