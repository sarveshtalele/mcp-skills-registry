"""Registry entrypoint for the unified reverse-engineering skill.

One skill, two modes:

- **remote** — given a ``repo_url`` (github.com), clones the repo and runs the
  full static-analysis pipeline (System Design Document + report + evaluation).
- **local** — given a ``repo_path`` (a directory the server can read), inventories
  languages, entry points, and modules and returns spec + architecture scaffolds.

Exactly one of ``repo_url`` / ``repo_path`` must be provided. The returned object
is the authoritative analysis result.
"""

from __future__ import annotations

import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from engine.pipeline import run_pipeline  # noqa: E402

_REPORT_CHAR_CAP = 60_000

_LANG_BY_EXT = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript/React",
    ".jsx": "JavaScript/React", ".java": "Java", ".cs": "C#", ".rb": "Ruby",
    ".go": "Go", ".php": "PHP", ".sql": "SQL", ".html": "HTML", ".css": "CSS",
}
_ENTRY_HINTS = ("main", "app", "index", "server", "program", "startup", "wsgi", "manage")
_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}


def run(inputs: dict) -> dict:
    """Analyse a remote repo URL or a local repo path (exactly one)."""
    repo_url = (inputs.get("repo_url") or "").strip()
    repo_path = (inputs.get("repo_path") or "").strip()

    if repo_url and repo_path:
        raise ValueError("provide either repo_url OR repo_path, not both")
    if repo_url:
        return _analyse_remote(repo_url)
    if repo_path:
        return _analyse_local(repo_path)
    raise ValueError(
        "provide 'repo_url' (a github.com URL to clone) or 'repo_path' "
        "(a local directory the server can read)"
    )


# --- Remote mode (clone + full pipeline) ---------------------------------


def _analyse_remote(repo_url: str) -> dict:
    out_dir = Path(tempfile.mkdtemp(prefix="reveng_out_"))
    run_pipeline(repo_url, mode="heuristic", output_dir=str(out_dir))

    manifest_path = next(out_dir.rglob("manifest.json"), None)
    report_path = next(out_dir.rglob("*_report.md"), None)
    sdd_path = next(out_dir.rglob("*_sdd.json"), None)

    manifest = json.loads(manifest_path.read_text("utf-8")) if manifest_path else {}
    report = report_path.read_text("utf-8") if report_path else ""
    return {
        "mode": "remote",
        "repo_url": repo_url,
        "manifest": manifest,
        "report_markdown": report[:_REPORT_CHAR_CAP],
        "report_truncated": len(report) > _REPORT_CHAR_CAP,
        "sdd_available": sdd_path is not None,
    }


# --- Local mode (filesystem scan) ----------------------------------------


def _scan(root: Path) -> dict:
    langs: Counter[str] = Counter()
    entry_points: list[str] = []
    module_count = 0
    for path in root.rglob("*"):
        if any(part in _SKIP_DIRS for part in path.parts) or not path.is_file():
            continue
        lang = _LANG_BY_EXT.get(path.suffix.lower())
        if lang:
            langs[lang] += 1
            module_count += 1
            if path.stem.lower() in _ENTRY_HINTS and len(entry_points) < 15:
                entry_points.append(str(path.relative_to(root)))
    return {
        "languages": dict(langs.most_common()),
        "entry_points": entry_points,
        "module_count": module_count,
    }


def _analyse_local(repo_path: str) -> dict:
    root = Path(repo_path).expanduser()
    if not root.is_dir():
        raise ValueError(
            f"repo_path is not a readable directory: {repo_path!r}. For a remote "
            "repository pass 'repo_url' instead."
        )
    inventory = _scan(root)
    primary = next(iter(inventory["languages"]), "unknown")
    lang_rows = (
        "\n".join(f"- {k}: {v} files" for k, v in inventory["languages"].items())
        or "- (none detected)"
    )
    entries = "\n".join(f"- `{e}`" for e in inventory["entry_points"]) or "- _[NEEDS REVIEW]_"

    spec = f"""# Specification (reverse-engineered)

## Source
scanned `{root}`

## Detected stack
{lang_rows}

## Purpose & scope
_[NEEDS CLARIFICATION] — describe what the system does._

## Current capabilities
- _[NEEDS REVIEW]_ list user-facing capabilities.

## Constraints carried forward
- Data migrations, integrations, compliance obligations. _[NEEDS REVIEW]_
"""
    architecture = f"""# As-Is Architecture

## Primary language
{primary}

## Candidate entry points
{entries}

## Modules
{inventory['module_count']} source module(s) detected.

## Integrations
- _[NEEDS REVIEW]_ external systems, databases, queues.
"""
    return {
        "mode": "local",
        "repo_path": str(root),
        "spec_markdown": spec,
        "architecture_markdown": architecture,
        "inventory": inventory,
    }
