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
    sdd_path = next(out_dir.rglob("*_sdd.json"), None)

    manifest = json.loads(manifest_path.read_text("utf-8")) if manifest_path else {}
    sdd = json.loads(sdd_path.read_text("utf-8")) if sdd_path else {}

    # Render a code-free, chief-architect report from the structured SDD.
    report = _render_architect_report(sdd, repo_url)
    return {
        "mode": "remote",
        "repo_url": repo_url,
        "manifest": manifest,
        "report_markdown": report[:_REPORT_CHAR_CAP],
        "report_truncated": len(report) > _REPORT_CHAR_CAP,
        "sdd_available": sdd_path is not None,
    }


def _render_architect_report(sdd: dict, repo_url: str) -> str:
    """Build a stakeholder/architect report (system design, stack, DB, SDLC).

    Deterministic, prose + tables only — NO source-code blocks.
    """
    proj = sdd.get("project", {})
    summ = sdd.get("executive_summary", {})
    metrics = sdd.get("codebase_metrics", {})
    arch = sdd.get("architecture", {})
    data = sdd.get("data_architecture", {})
    api = sdd.get("api_catalog", {})
    deps = sdd.get("dependency_analysis", {})
    auth = sdd.get("auth_analysis", {})
    risks = sdd.get("risk_assessment", []) or []
    name = proj.get("name", "repository")

    def table(headers, rows):
        if not rows:
            return "_None detected._\n"
        out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
        out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
        return "\n".join(out) + "\n"

    lines: list[str] = []
    lines.append(f"# {name} — Architecture & System Design Report")
    lines.append(f"\n**Repository:** {repo_url}  ")
    lines.append(f"**Primary language:** {proj.get('primary_language', 'n/a')}  ")
    lines.append(f"**Platform:** {proj.get('platform', 'n/a')}  ")
    lines.append(f"**Architecture pattern:** {summ.get('architecture_pattern', 'n/a')}")

    lines.append("\n## 1. Executive Summary\n")
    lines.append(summ.get("purpose") or "_Purpose inferred from static analysis._")
    lines.append(f"\n- **Modernization priority:** {summ.get('modernization_priority', 'n/a')}")
    if summ.get("priority_reasoning"):
        lines.append(f"- **Why:** {summ['priority_reasoning']}")

    lines.append("\n## 2. Codebase Metrics\n")
    lines.append(
        table(
            ["Metric", "Value"],
            [
                ["Files analyzed", metrics.get("total_files_analyzed", 0)],
                ["Classes", metrics.get("total_classes", 0)],
                ["Methods", metrics.get("total_methods", 0)],
                ["API endpoints", metrics.get("total_api_endpoints", 0)],
                ["Dead-code files", metrics.get("dead_code_files", 0)],
            ],
        )
    )

    lines.append("\n## 3. System Design\n")
    lines.append(f"**Style:** {arch.get('style', 'n/a')}\n")
    layers = arch.get("layers", []) or proj.get("architecture_layers", [])
    if layers:
        lines.append("**Layers (top → bottom):**\n")
        lines += [f"{i}. {layer}" for i, layer in enumerate(layers, 1)]
    comps = [c.get("name", str(c)) if isinstance(c, dict) else str(c) for c in arch.get("components", [])][:15]
    if comps:
        lines.append("\n**Key components:** " + ", ".join(f"`{c}`" for c in comps))

    lines.append("\n## 4. Technology Stack\n")
    stack = proj.get("tech_stack", []) or []
    lang_dist = metrics.get("language_distribution", {}) or {}
    lines.append(table(["Language", "Files"], list(lang_dist.items())[:12]))
    if stack:
        lines.append("\n**Frameworks / libraries:** " + ", ".join(f"`{s}`" for s in stack[:25]))

    lines.append("\n## 5. Database Design\n")
    if data.get("has_schema"):
        lines.append(
            f"{data.get('entity_count', 0)} entit(y/ies), "
            f"{data.get('relationship_count', 0)} relationship(s).\n"
        )
        ent_rows = [
            [e.get("name", ""), e.get("table", "—"), len(e.get("fields", [])), len(e.get("relationships", []))]
            for e in (data.get("entities", []) or [])[:25]
        ]
        lines.append(table(["Entity", "Table", "Fields", "Relationships"], ent_rows))
    else:
        lines.append("_No persistent data model detected via static analysis._")

    lines.append("\n## 6. API Surface\n")
    eps = api.get("endpoints", []) or []
    ep_rows = [[", ".join(ep.get("http_methods", [])) or "—", ep.get("path", "")] for ep in eps[:25]]
    lines.append(f"Total endpoints: {api.get('total_endpoints', 0)}\n")
    lines.append(table(["Methods", "Path"], ep_rows))

    lines.append("\n## 7. Security & Access Control\n")
    lines.append(f"- **Auth type:** {auth.get('auth_type', 'Not analyzed')}")
    if auth.get("auth_frameworks"):
        lines.append(f"- **Frameworks:** {', '.join(auth['auth_frameworks'])}")

    lines.append("\n## 8. Dependencies & Coupling\n")
    lines.append(f"External dependencies: {deps.get('total_unique_external_deps', 0)}\n")
    top = deps.get("top_10_most_connected", []) or []
    lines.append(
        table(["Module", "Connections"], [[m.get("module", ""), m.get("connections", 0)] for m in top[:10]])
    )

    lines.append("\n## 9. SDLC & Quality Assessment\n")
    lines.append(
        "- **Maintainability:** higher coupling in the modules above raises change risk.\n"
        f"- **Dead code:** {metrics.get('dead_code_files', 0)} unreferenced file(s) — candidates for removal.\n"
        "- **Testing:** confirm automated coverage exists for the high-connection modules.\n"
        "- **CI/CD & observability:** validate pipeline, IaC, logging, and monitoring against the stack above."
    )

    lines.append("\n## 10. Risks & Recommendations\n")
    if risks:
        for r in risks[:8]:
            sev = r.get("severity", r.get("level", ""))
            issue = r.get("issue", r.get("risk", r.get("area", "")))
            rec = r.get("recommendation", "")
            lines.append(f"- **[{sev}] {issue}** — {rec}")
    for concern in summ.get("tech_debt_concerns", [])[:6]:
        lines.append(f"- {concern}")

    lines.append("\n---\n_Generated by the legacy-discovery skill (static analysis). "
                 "This report is the authoritative analysis; treat it as final._")
    return "\n".join(lines)


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
