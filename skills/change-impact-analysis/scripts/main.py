"""Registry entrypoint for the change-impact-analysis skill.

Wraps the skill's analysis engine behind the registry contract
``run(inputs) -> dict``. Returns the structured impact result (dependency graph
impact, contract violations, deterministic risk score) as JSON-safe data.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from engine.contract_validator import ContractValidator  # noqa: E402
from engine.graph_builder import DependencyGraphBuilder  # noqa: E402
from engine.impact_analyzer import ImpactAnalyzer  # noqa: E402
from engine.ownership_parser import OwnershipParser  # noqa: E402
from engine.risk_scorer import RiskScorer  # noqa: E402


def run(inputs: dict) -> dict:
    """Run change-impact analysis for a set of changed files.

    Inputs:
        repo_path:     repository root to analyse (default ".").
        changed_files: list of changed file paths (relative to the repo).
        base_branch:   base branch for contract comparison (default "main").
    """
    repo_path = Path(inputs.get("repo_path") or ".").resolve()
    base_branch = inputs.get("base_branch") or "main"
    changed = inputs.get("changed_files") or []
    if isinstance(changed, str):
        changed = [changed]

    if not repo_path.exists():
        raise ValueError(f"repo_path not found: {repo_path}")

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
