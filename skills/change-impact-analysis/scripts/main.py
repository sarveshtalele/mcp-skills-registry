"""Registry entrypoint for the change-impact-analysis skill.

Wraps the skill's analysis engine behind the registry contract
``run(inputs) -> dict``. Returns the structured impact result (dependency graph
impact, contract violations, deterministic risk score) as JSON-safe data.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from engine.contract_validator import ContractValidator  # noqa: E402
from engine.graph_builder import DependencyGraphBuilder  # noqa: E402
from engine.impact_analyzer import ImpactAnalyzer  # noqa: E402
from engine.ownership_parser import OwnershipParser  # noqa: E402
from engine.risk_scorer import RiskScorer  # noqa: E402


def _clone(repo_url: str) -> Path:
    """Shallow-clone a public repo to a temp dir; return its path."""
    dest = Path(tempfile.mkdtemp(prefix="cia_")) / "repo"
    subprocess.run(
        ["git", "clone", "--depth", "1", repo_url, str(dest)],
        check=True, capture_output=True, text=True, timeout=80,
    )
    return dest


def run(inputs: dict) -> dict:
    """Run change-impact analysis.

    Inputs (provide a repo source):
        repo_url:      public git URL to shallow-clone and analyse (web-friendly), OR
        repo_path:     a local repository root the server can read.
        changed_files: list of changed file paths (relative to the repo).
        base_branch:   base branch for contract comparison (default "main").
    """
    repo_url = (inputs.get("repo_url") or "").strip()
    base_branch = inputs.get("base_branch") or "main"
    changed = inputs.get("changed_files") or []
    if isinstance(changed, str):
        changed = [c.strip() for c in changed.split(",") if c.strip()]

    if repo_url:
        try:
            repo_path = _clone(repo_url).resolve()
        except subprocess.CalledProcessError as exc:
            raise ValueError(f"could not clone {repo_url}: {exc.stderr.strip()[:200]}") from exc
    else:
        repo_path = Path(inputs.get("repo_path") or "").expanduser().resolve()
        if not inputs.get("repo_path") or not repo_path.is_dir():
            raise ValueError(
                "provide 'repo_url' (a public git URL) or 'repo_path' (a local "
                "directory the server can read)"
            )

    dep_graph = DependencyGraphBuilder(repo_path).build()
    ownership = OwnershipParser(repo_path).parse()
    violations = ContractValidator(repo_path, base_branch).validate()
    impact = ImpactAnalyzer(dep_graph, ownership, repo_path).analyze(changed)
    risk = RiskScorer().score(impact, violations)

    result = {
        "repo_path": str(repo_path),
        "base_branch": base_branch,
        "changed_files": changed,
        "impact": impact,
        "contract_violations": violations,
        "risk": risk,
    }
    # Normalise to plain JSON types (engine may emit sets/tuples).
    return json.loads(json.dumps(result, default=str))
