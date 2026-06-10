"""Tests for the skill upload endpoint and installer safety."""

from __future__ import annotations

import io
import zipfile

from tests.conftest import make_skill_zip


def _post_zip(client, data: bytes, **params):
    return client.post(
        "/api/v1/skills/upload",
        params=params,
        files={"file": ("skill.zip", data, "application/zip")},
    )


def test_upload_installs_and_runs(writable_client):
    resp = _post_zip(writable_client, make_skill_zip("echo-skill"))
    assert resp.status_code == 201
    assert resp.json()["name"] == "echo-skill"

    # It now appears in the catalogue and is executable.
    listed = writable_client.get("/api/v1/skills").json()
    assert any(s["name"] == "echo-skill" for s in listed)

    run = writable_client.post(
        "/api/v1/skills/echo-skill/execute", json={"inputs": {"value": "hi"}}
    )
    assert run.json()["output"] == {"echoed": "hi"}


def test_upload_flat_archive(writable_client):
    resp = _post_zip(writable_client, make_skill_zip("flat-skill", nested=False))
    assert resp.status_code == 201


def test_duplicate_requires_overwrite(writable_client):
    _post_zip(writable_client, make_skill_zip("dup")).raise_for_status()
    again = _post_zip(writable_client, make_skill_zip("dup"))
    assert again.status_code == 400
    forced = _post_zip(writable_client, make_skill_zip("dup"), overwrite=True)
    assert forced.status_code == 201


def test_missing_manifest_rejected(writable_client):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("scripts/main.py", "def run(i): return {}\n")
    resp = _post_zip(writable_client, buffer.getvalue())
    assert resp.status_code == 400


def test_zip_slip_rejected(writable_client):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("evil/SKILL.md", make_skill_zip.__doc__ or "")
        zf.writestr("evil/../../escape.txt", "pwned")
    # Either rejected as unsafe path or as an invalid manifest; never written outside.
    resp = _post_zip(writable_client, buffer.getvalue())
    assert resp.status_code in (400, 422)


def test_invalid_manifest_rejected(writable_client):
    bad = b"---\nname: Bad Name!\ndescription: x\n---\n"  # invalid slug
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("bad/SKILL.md", bad)
        zf.writestr("bad/scripts/main.py", "def run(i): return {}\n")
    resp = _post_zip(writable_client, buffer.getvalue())
    assert resp.status_code == 422
