"""
Report Generator
Renders the final Impact Report (Markdown), machine-readable JSON, and a
Deployment Checklist from the aggregated analysis result dictionary.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class ReportGenerator:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_markdown(self, result: Dict[str, Any]) -> Path:
        out = self.output_dir / "impact_report.md"
        out.write_text(self._build_markdown(result), encoding="utf-8")
        return out

    def generate_json(self, result: Dict[str, Any]) -> Path:
        out = self.output_dir / "impact_analysis.json"
        out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
        return out

    def generate_checklist(self, result: Dict[str, Any]) -> Path:
        out = self.output_dir / "deployment_checklist.md"
        out.write_text(self._build_checklist(result), encoding="utf-8")
        return out

    # ------------------------------------------------------------------
    # Markdown report
    # ------------------------------------------------------------------

    def _build_markdown(self, result: Dict[str, Any]) -> str:
        impact = result["impact"]
        risk = result["risk"]
        violations = result.get("contract_violations", [])
        changed = impact.get("changed_files", [])

        breaking_count = len([v for v in violations if v.get("severity") == "breaking"])
        apis = impact.get("impacted_apis", [])
        modules = impact.get("impacted_modules", [])

        lines: List[str] = [
            "# Change Impact Analysis Report",
            "",
            f"**Generated:** {self.ts}  ",
            f"**Repository:** `{result.get('repo_path', 'N/A')}`",
            "",
            "---",
            "",
            "## Executive Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Changed Files | {len(changed)} |",
            f"| Directly Affected Modules | {impact.get('direct_impact_count', 0)} |",
            f"| Transitively Affected Modules | {impact.get('transitive_impact_count', 0)} |",
            f"| Impacted API Endpoints | {len(apis)} |",
            f"| Breaking Contract Changes | {breaking_count} |",
            f"| Consumer Apps Affected | {len(impact.get('consumer_apps', []))} |",
            f"| **Deployment Risk Score** | **{risk['score']}/100 — {risk['level']}** |",
            "",
            "---",
            "",
            "## Deployment Risk Score",
            "",
            "```",
            f"Risk Score : {risk['score']}/100",
            f"Risk Level : {risk['level']}",
            f"Action     : {risk['action']}",
            "```",
            "",
            "### Risk Factor Breakdown",
            "",
            "| Factor | Points | Detail |",
            "|--------|--------|--------|",
        ]

        for f in risk.get("factors", []):
            lines.append(f"| `{f['factor']}` | +{f['points']} | {f['detail']} |")

        lines += [
            "",
            "---",
            "",
            "## Changed Files",
            "",
        ]
        for f in changed:
            lines.append(f"- `{f}`")

        lines += [
            "",
            "---",
            "",
            "## Impacted API Endpoints",
            "",
        ]
        if apis:
            lines += ["| File | Owners | Proximity |", "|------|--------|-----------|"]
            for api in apis:
                owners = ", ".join(api.get("owners") or ["—"])
                lines.append(f"| `{api['path']}` | {owners} | {api.get('proximity','?')} |")
        else:
            lines.append("_No API endpoints in the blast radius._")

        lines += [
            "",
            "---",
            "",
            "## Impacted Modules",
            "",
            "| Module | Type | Proximity | Owners | Risk Factors |",
            "|--------|------|-----------|--------|--------------|",
        ]
        for m in sorted(modules, key=lambda x: (x.get("change_proximity", ""), x.get("path", ""))):
            owners = ", ".join(m.get("owners") or ["—"])
            rfs = ", ".join(m.get("risk_factors") or ["—"])
            lines.append(f"| `{m['path']}` | {m['module_type']} | {m['change_proximity']} | {owners} | {rfs} |")

        lines += [
            "",
            "---",
            "",
            "## Potential Regression Areas",
            "",
        ]
        regression_areas = impact.get("regression_areas", [])
        if regression_areas:
            for area in regression_areas:
                lines.append(f"- {area}")
        else:
            lines.append("_No high-risk regression areas identified._")

        lines += [
            "",
            "---",
            "",
            "## Required Test Suites",
            "",
        ]
        for suite in impact.get("required_test_suites", []):
            lines.append(f"- [ ] `{suite}`")

        lines += [
            "",
            "---",
            "",
            "## Consumer Applications Affected",
            "",
        ]
        consumers = impact.get("consumer_apps", [])
        if consumers:
            for c in consumers:
                lines.append(f"- `{c}`")
        else:
            lines.append("_No consumer applications identified._")

        lines += [
            "",
            "---",
            "",
            "## API Contract Violations",
            "",
        ]
        if violations:
            lines += ["| Type | Severity | Endpoint | Detail |", "|------|----------|----------|--------|"]
            for v in violations:
                lines.append(
                    f"| `{v.get('type', '?')}` | {v.get('severity', '?')} | {v.get('endpoint', '?')} | {v.get('detail', '?')} |"
                )
        else:
            lines.append("_No contract violations detected._")

        lines += [
            "",
            "---",
            "",
            "_Report generated by **Change Impact Analysis Skill v1.0.0**_",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Deployment checklist
    # ------------------------------------------------------------------

    def _build_checklist(self, result: Dict[str, Any]) -> str:
        risk = result["risk"]
        impact = result["impact"]
        score = risk["score"]
        level = risk["level"]

        # Collect all unique owners
        all_owners = sorted({
            o for m in impact.get("impacted_modules", [])
            for o in (m.get("owners") or [])
        })

        lines: List[str] = [
            "# Deployment Checklist",
            "",
            f"**Date:** {self.ts}  ",
            f"**Risk Level:** {level} ({score}/100)  ",
            f"**Action:** {risk['action']}",
            "",
            "---",
            "",
            "## Pre-Deployment Sign-Off",
            "",
            "- [ ] Change impact report reviewed by: ___________",
            f"- [ ] Risk score acknowledged: **{score}/100 ({level})**",
            "- [ ] Rollback plan documented and communicated",
        ]

        if score > 60:
            lines.append("- [ ] Senior engineer approval obtained")
        if score > 80:
            lines.append("- [ ] Tech lead / engineering manager sign-off")
            lines.append("- [ ] Incident response team notified and on standby")

        lines += [
            "",
            "## Required Tests",
            "",
        ]
        for suite in impact.get("required_test_suites", []):
            lines.append(f"- [ ] `{suite}`")

        if score > 60:
            lines += [
                "",
                "- [ ] Full regression suite (HIGH/CRITICAL risk)",
                "- [ ] Load / performance test on affected endpoints",
            ]

        lines += [
            "",
            "## Owner Notifications",
            "",
        ]
        if all_owners:
            for owner in all_owners:
                lines.append(f"- [ ] Notify: **{owner}**")
        else:
            lines.append("_No owners identified — ensure the team is informed manually._")

        lines += [
            "",
            "## Post-Deployment Verification",
            "",
            "- [ ] Monitor error rate for ≥ 30 minutes post-deploy",
            "- [ ] Verify affected API endpoints respond correctly",
            "- [ ] Confirm consumer applications are functioning",
            "- [ ] Check database migration applied cleanly (if applicable)",
            "- [ ] Update deployment log / release notes",
        ]

        if level in ("HIGH", "CRITICAL"):
            lines += [
                "",
                "## High-Risk Safeguards",
                "",
                "- [ ] Feature flag / kill switch in place for rollback",
                "- [ ] Real-time log monitoring active (error spikes)",
                "- [ ] Canary or blue-green deployment strategy used",
                "- [ ] PagerDuty / alerting thresholds tightened for 24h",
            ]

        lines += [
            "",
            "---",
            "_Checklist generated by **Change Impact Analysis Skill v1.0.0**_",
        ]
        return "\n".join(lines)
