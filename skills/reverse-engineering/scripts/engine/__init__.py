"""
Reverse Engineer Skill — Engine Package
========================================
Public API for the reverse engineering pipeline.

This package provides a complete static analysis engine that clones any
GitHub repository and produces five professional output files:

1. ``{repo_name}_sdd.json``         — System Design Document (JSON)
2. ``{repo_name}_dashboard.html``   — Stakeholder HTML Dashboard
3. ``{repo_name}_report.md``        — Technical Markdown Report
4. ``{repo_name}_evaluation.md``    — Automated Quality Evaluation
5. ``manifest.json``                — Run manifest with metrics and file index

Example::

    from engine.pipeline import run_pipeline
    run_pipeline("https://github.com/nopSolutions/nopCommerce")
"""

__version__ = "3.0.0"
__author__  = "Reverse Engineer Skill"

from engine.pipeline import run_pipeline, clone_repo, repo_name_from_url

__all__ = ["run_pipeline", "clone_repo", "repo_name_from_url"]
