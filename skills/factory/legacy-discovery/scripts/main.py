"""legacy-discovery — reverse-engineer a legacy application.

If ``repo_path`` points at a real directory, performs a lightweight static scan
(language mix by file extension, candidate entry points, module count). Otherwise
works from ``app_description``. Emits spec.md and architecture.md scaffolds.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

_LANG_BY_EXT = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript/React",
    ".jsx": "JavaScript/React", ".java": "Java", ".cs": "C#", ".rb": "Ruby",
    ".go": "Go", ".php": "PHP", ".sql": "SQL", ".html": "HTML", ".css": "CSS",
}
_ENTRY_HINTS = ("main", "app", "index", "server", "program", "startup", "wsgi", "manage")
_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}


def _scan(root: Path) -> dict:
    langs: Counter[str] = Counter()
    entry_points: list[str] = []
    module_count = 0
    for path in root.rglob("*"):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file():
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


def run(inputs: dict) -> dict:
    repo_path = inputs.get("repo_path")
    description = inputs.get("app_description")

    inventory: dict = {"languages": {}, "entry_points": [], "module_count": 0}
    source = description or "(no description provided)"
    if repo_path:
        root = Path(repo_path).expanduser()
        if root.is_dir():
            inventory = _scan(root)
            source = f"scanned `{root}`"

    primary = next(iter(inventory["languages"]), "unknown")
    lang_rows = "\n".join(f"- {k}: {v} files" for k, v in inventory["languages"].items()) or "- (none detected)"
    entries = "\n".join(f"- `{e}`" for e in inventory["entry_points"]) or "- _[NEEDS REVIEW]_"

    spec = f"""# Legacy System Specification

## Source
{source}

## Detected stack
{lang_rows}

## Purpose & scope
{description or "_[NEEDS CLARIFICATION] — describe what the system does._"}

## Current capabilities (reverse-engineered)
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

## Risks & unknowns
- _[NEEDS REVIEW]_ undocumented behaviour, dead code, tight coupling.
"""
    return {
        "spec_markdown": spec,
        "architecture_markdown": architecture,
        "inventory": inventory,
    }
