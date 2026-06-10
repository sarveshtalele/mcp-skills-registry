"""Registry entrypoint for the reverse-engineering skill.

Wraps the static-analysis pipeline behind the registry contract
``run(inputs) -> dict``. Clones the target repository, runs heuristic analysis,
and returns the run manifest plus the generated Markdown report (size-capped).
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from engine.pipeline import run_pipeline  # noqa: E402

_REPORT_CHAR_CAP = 60_000  # keep output within the registry's size limit


def run(inputs: dict) -> dict:
    """Reverse-engineer a public GitHub repository via static analysis.

    Inputs:
        repo_url: GitHub repository URL to analyse (required).
    """
    repo_url = inputs.get("repo_url")
    if not repo_url:
        raise ValueError("repo_url is required")

    out_dir = Path(tempfile.mkdtemp(prefix="reveng_out_"))
    run_pipeline(repo_url, mode="heuristic", output_dir=str(out_dir))

    manifest_path = next(out_dir.rglob("manifest.json"), None)
    report_path = next(out_dir.rglob("*_report.md"), None)
    sdd_path = next(out_dir.rglob("*_sdd.json"), None)

    manifest = json.loads(manifest_path.read_text("utf-8")) if manifest_path else {}
    report = report_path.read_text("utf-8") if report_path else ""
    truncated = len(report) > _REPORT_CHAR_CAP

    return {
        "repo_url": repo_url,
        "manifest": manifest,
        "report_markdown": report[:_REPORT_CHAR_CAP],
        "report_truncated": truncated,
        "sdd_available": sdd_path is not None,
    }
