"""Create a ServiceNow incident via the Table API (stdlib only)."""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request


def run(inputs: dict) -> dict:
    instance = os.getenv("SERVICENOW_INSTANCE", "").strip()
    user = os.getenv("SERVICENOW_USER", "")
    password = os.getenv("SERVICENOW_PASSWORD", "")
    if not (instance and user and password):
        raise RuntimeError(
            "ServiceNow is not configured. Set SERVICENOW_INSTANCE, "
            "SERVICENOW_USER, and SERVICENOW_PASSWORD environment variables."
        )
    base = f"https://{instance}.service-now.com" if "." not in instance else f"https://{instance}"

    payload = {
        "short_description": inputs["short_description"],
        "description": inputs.get("description") or "",
        "urgency": str(inputs.get("urgency") or "3"),
    }
    data = json.dumps(payload).encode("utf-8")
    auth = base64.b64encode(f"{user}:{password}".encode()).decode()
    req = urllib.request.Request(f"{base}/api/now/table/incident", data=data, method="POST")
    req.add_header("Authorization", f"Basic {auth}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            body = json.loads(resp.read().decode("utf-8")).get("result", {})
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"ServiceNow API error {exc.code}: {detail}") from exc

    return {"number": body.get("number", ""), "sys_id": body.get("sys_id", "")}
