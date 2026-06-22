"""Tests for the skill upload endpoint and installer safety."""

from __future__ import annotations

import io
import stat
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


def test_delete_and_reupload(writable_client):
    _post_zip(writable_client, make_skill_zip("temp-skill")).raise_for_status()
    assert writable_client.delete("/api/v1/skills/temp-skill").status_code == 204
    assert writable_client.get("/api/v1/skills/temp-skill").status_code == 404
    # Re-upload the same name succeeds.
    again = _post_zip(writable_client, make_skill_zip("temp-skill"))
    assert again.status_code == 201


def test_delete_unknown_skill_404(writable_client):
    assert writable_client.delete("/api/v1/skills/nope").status_code == 404


def test_upload_reports_installed_files(writable_client):
    resp = _post_zip(writable_client, make_skill_zip("tree-skill"))
    assert resp.status_code == 201
    files = resp.json()["installed_files"]
    assert "SKILL.md" in files and "scripts/main.py" in files


def test_upload_flat_archive(writable_client):
    resp = _post_zip(writable_client, make_skill_zip("flat-skill", nested=False))
    assert resp.status_code == 201


def test_reupload_overwrites_by_default(writable_client):
    _post_zip(writable_client, make_skill_zip("dup")).raise_for_status()
    again = _post_zip(writable_client, make_skill_zip("dup"))  # overwrite defaults True
    assert again.status_code == 201
    # Explicit overwrite=false blocks replacing an existing skill.
    blocked = _post_zip(writable_client, make_skill_zip("dup"), overwrite=False)
    assert blocked.status_code == 400


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


def test_traversal_wrapper_rejected(writable_client):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        with zipfile.ZipFile(io.BytesIO(make_skill_zip("traversal-root"))) as source:
            for info in source.infolist():
                zf.writestr(f"../{info.filename}", source.read(info))
    resp = _post_zip(writable_client, buffer.getvalue())
    assert resp.status_code == 400


def test_symlink_member_rejected(writable_client):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        with zipfile.ZipFile(io.BytesIO(make_skill_zip("link-skill"))) as source:
            for info in source.infolist():
                zf.writestr(info, source.read(info))
        link = zipfile.ZipInfo("link-skill/docs/latest")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        zf.writestr(link, "README.md")
    resp = _post_zip(writable_client, buffer.getvalue())
    assert resp.status_code == 400


def test_imperfect_manifest_is_coerced_not_rejected(writable_client):
    """A non-slug name is coerced (uploads are never blocked on style)."""
    bad = b"---\nname: Bad Name!\ndescription: x\n---\n"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("bad/SKILL.md", bad)
        zf.writestr("bad/scripts/main.py", "def run(i): return {}\n")
    resp = _post_zip(writable_client, buffer.getvalue())
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "bad-name"  # coerced slug
    assert "SKILL.md" in body["installed_files"]
