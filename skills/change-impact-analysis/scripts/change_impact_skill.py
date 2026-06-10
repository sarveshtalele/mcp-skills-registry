#!/usr/bin/env python3
"""
Change Impact Analysis Skill — CLI Entry Point

Usage
-----
# Explicit file list
python change_impact_skill.py --changed-files src/api/users.py src/models/user.py

# Auto-detect from git diff against base branch
python change_impact_skill.py --from-git --base-branch main

# Custom repo path and output directory
python change_impact_skill.py --repo-path /path/to/repo --from-git --output /tmp/impact
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from engine.graph_builder import DependencyGraphBuilder
from engine.impact_analyzer import ImpactAnalyzer
from engine.risk_scorer import RiskScorer
from engine.contract_validator import ContractValidator
from engine.ownership_parser import OwnershipParser
from engine.report_generator import ReportGenerator

_DIVIDER = "=" * 64


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Change Impact Analysis Skill",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--repo-path", default=".",
        help="Root of the repository to analyse (default: current directory)",
    )
    p.add_argument(
        "--changed-files", nargs="+", metavar="FILE",
        help="Explicit list of changed file paths",
    )
    p.add_argument(
        "--from-git", action="store_true",
        help="Auto-detect changed files from `git diff --name-only <base>`",
    )
    p.add_argument(
        "--base-branch", default="main",
        help="Base branch for git diff (default: main)",
    )
    p.add_argument(
        "--output", default=None,
        help="Output directory (default: <repo-root>/change-impact-output/)",
    )
    p.add_argument(
        "--format", choices=["markdown", "json", "both"], default="both",
        help="Output format(s) to generate (default: both)",
    )
    p.add_argument(
        "--json-only", action="store_true",
        help="Emit the JSON result to stdout and exit (no files written)",
    )
    return p.parse_args()


def get_changed_files_from_git(repo_path: Path, base_branch: str) -> list:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{base_branch}...HEAD"],
            capture_output=True, text=True, cwd=repo_path, check=True,
        )
        files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
        if not files:
            # Fall back to staged / working-tree changes
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                capture_output=True, text=True, cwd=repo_path, check=False,
            )
            files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
        return files
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"  [warn] git diff failed: {exc}", file=sys.stderr)
        return []


def main() -> int:
    args = parse_args()
    repo_path = Path(args.repo_path).resolve()

    if not repo_path.exists():
        print(f"[error] Repository path not found: {repo_path}", file=sys.stderr)
        return 1

    # Resolve changed files
    if args.from_git:
        changed_files = get_changed_files_from_git(repo_path, args.base_branch)
        if not changed_files:
            print("[warn] No changed files detected via git. Nothing to analyse.")
            return 0
    elif args.changed_files:
        changed_files = args.changed_files
    else:
        print("[error] Provide --changed-files <files...> or --from-git", file=sys.stderr)
        return 1

    output_dir = Path(args.output) if args.output else repo_path / "change-impact-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not args.json_only:
        print(f"\n{_DIVIDER}")
        print("  CHANGE IMPACT ANALYSIS SKILL  v1.0.0")
        print(_DIVIDER)
        print(f"  Repository : {repo_path}")
        print(f"  Changed    : {len(changed_files)} file(s)")
        print(f"  Base branch: {args.base_branch}")
        print(f"  Output     : {output_dir}")
        print(_DIVIDER)

    # ── Phase 1: Build dependency graph ───────────────────────────────
    _step(1, 5, "Building dependency graph", args.json_only)
    graph_builder = DependencyGraphBuilder(repo_path)
    dep_graph = graph_builder.build()
    _log(f"Nodes: {len(dep_graph.nodes)}, Edges: {sum(len(v) for v in dep_graph.edges.values())}", args.json_only)

    # ── Phase 2: Parse ownership metadata ────────────────────────────
    _step(2, 5, "Parsing ownership metadata", args.json_only)
    ownership_parser = OwnershipParser(repo_path)
    ownership_map = ownership_parser.parse()

    # ── Phase 3: Validate API contracts ──────────────────────────────
    _step(3, 5, "Validating API contracts", args.json_only)
    contract_validator = ContractValidator(repo_path, args.base_branch)
    contract_violations = contract_validator.validate()
    _log(f"Violations found: {len(contract_violations)}", args.json_only)

    # ── Phase 4: Analyze change impact ───────────────────────────────
    _step(4, 5, "Analysing change impact", args.json_only)
    impact_analyzer = ImpactAnalyzer(dep_graph, ownership_map, repo_path)
    impact = impact_analyzer.analyze(changed_files)
    _log(
        f"Direct: {impact['direct_impact_count']}, Transitive: {impact['transitive_impact_count']}",
        args.json_only,
    )

    # ── Phase 5: Calculate risk score ────────────────────────────────
    _step(5, 5, "Calculating deployment risk score", args.json_only)
    risk_scorer = RiskScorer()
    risk_result = risk_scorer.score(impact, contract_violations)

    # ── Assemble result ───────────────────────────────────────────────
    result = {
        "repo_path": str(repo_path),
        "base_branch": args.base_branch,
        "impact": impact,
        "contract_violations": contract_violations,
        "risk": risk_result,
    }

    # ── JSON-only mode ────────────────────────────────────────────────
    if args.json_only:
        print(json.dumps(result, indent=2, default=str))
        return 0

    # ── Write output files ────────────────────────────────────────────
    print("\n  Generating reports...")
    report_gen = ReportGenerator(output_dir)

    paths = {}
    if args.format in ("markdown", "both"):
        paths["report"] = report_gen.generate_markdown(result)
        print(f"  [ok] Impact Report   : {paths['report']}")

    if args.format in ("json", "both"):
        paths["json"] = report_gen.generate_json(result)
        print(f"  [ok] Analysis JSON   : {paths['json']}")

    paths["checklist"] = report_gen.generate_checklist(result)
    print(f"  [ok] Deploy Checklist: {paths['checklist']}")

    # ── Summary ───────────────────────────────────────────────────────
    score = risk_result["score"]
    level = risk_result["level"]
    bar = _risk_bar(score)

    print(f"\n{_DIVIDER}")
    print(f"  RISK SCORE  {score:3d}/100  {bar}  {level}")
    print(f"  Action      {risk_result['action']}")
    print(f"  APIs        {len(impact['impacted_apis'])} endpoint(s) affected")
    print(f"  Modules     {impact['direct_impact_count']} direct | {impact['transitive_impact_count']} transitive")
    print(f"  Consumers   {len(impact['consumer_apps'])} application(s)")
    print(f"  Contracts   {len(contract_violations)} violation(s)")
    print(_DIVIDER + "\n")

    return 0


def _step(n: int, total: int, label: str, silent: bool) -> None:
    if not silent:
        print(f"[{n}/{total}] {label}...")


def _log(msg: str, silent: bool) -> None:
    if not silent:
        print(f"      {msg}")


def _risk_bar(score: int) -> str:
    filled = score // 10
    return "[" + "#" * filled + "." * (10 - filled) + "]"


if __name__ == "__main__":
    sys.exit(main())
