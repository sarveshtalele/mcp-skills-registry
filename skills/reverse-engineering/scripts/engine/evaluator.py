"""
Pipeline Evaluator
==================
Automated quality-scoring engine that runs after the reverse engineering
pipeline completes and produces a structured evaluation report.

The evaluator scores six sections across a 100-point scale:

+-------------------------------------------+--------+
| Section                                   | Weight |
+===========================================+========+
| 1. Parsing Quality                        | 20 pts |
| 2. API Endpoint Detection                 | 20 pts |
| 3. Dead Code Analysis                     | 15 pts |
| 4. Entity / Data Architecture             | 15 pts |
| 5. Dependency Graph                       | 15 pts |
| 6. AI Analysis Quality                    | 15 pts |
+-------------------------------------------+--------+

Each check emits a status of **PASS**, **WARN**, or **FAIL** with an
explanatory message.  The overall confidence band is:

- **HIGH**      ≥ 80 pts
- **MEDIUM**    ≥ 60 pts
- **LOW**       ≥ 40 pts
- **VERY LOW**  < 40 pts

Entry point: :func:`evaluate_pipeline_output`
Markdown writer: :func:`write_evaluation_md`
"""

import datetime
import re
from pathlib import Path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_pipeline_output(
    parsed,
    report,
    endpoints,
    dead_code,
    dep_map,
    graphviz_code,
    tech_stack,
    summary,
    modernization,
    db_schema,
    data_boundaries,
    repo_name,
):
    """Run all evaluation checks and return a structured result dict.

    Args:
        parsed (list[dict]): Parsed file records from
            :func:`engine.parsers.parse_file`.
        report (dict): Metrics from :func:`engine.analyzer.generate_report`.
        endpoints (list[dict]): API endpoints from
            :func:`engine.analyzer.extract_api_endpoints`.
        dead_code (dict): Dead-code results from
            :func:`engine.analyzer.detect_dead_code`.
        dep_map (dict[str, set]): Dependency map from
            :func:`engine.analyzer.build_dependency_map`.
        mermaid_code (str): Mermaid diagram string from
            :func:`engine.analyzer.generate_mermaid`.
        tech_stack (list[str]): Detected technologies.
        summary (dict): AI executive summary.
        modernization (dict): AI modernization roadmap.
        db_schema (dict | None): Entity schema from
            :func:`engine.analyzer.detect_database_schema`.
        data_boundaries (list | None): Microservice boundaries from
            :func:`engine.analyzer.suggest_microservice_data_boundaries`.
        repo_name (str): Repository name for display.

    Returns:
        dict: Evaluation result with keys:

        - ``"repo_name"``          — str
        - ``"generated_at"``       — ISO-8601 timestamp string
        - ``"total_score"``        — int (0–100)
        - ``"confidence"``         — "HIGH" | "MEDIUM" | "LOW" | "VERY LOW"
        - ``"sections"``           — list of section dicts
        - ``"summary_lines"``      — list of human-readable summary strings
        - ``"recommendations"``    — list of recommendation strings
    """
    sections = [
        _eval_parsing_quality(parsed, report),
        _eval_api_endpoints(endpoints, parsed),
        _eval_dead_code(dead_code, report),
        _eval_data_architecture(db_schema, data_boundaries, parsed),
        _eval_dependency_graph(dep_map, graphviz_code, tech_stack),
        _eval_ai_analysis(summary, modernization),
    ]

    total = sum(s["score"] for s in sections)
    confidence = (
        "HIGH"      if total >= 80 else
        "MEDIUM"    if total >= 60 else
        "LOW"       if total >= 40 else
        "VERY LOW"
    )

    summary_lines = _build_summary_lines(sections, total, confidence, repo_name)
    recommendations = _collect_recommendations(sections)

    return {
        "repo_name":       repo_name,
        "generated_at":    datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "total_score":     total,
        "max_score":       100,
        "confidence":      confidence,
        "sections":        sections,
        "summary_lines":   summary_lines,
        "recommendations": recommendations,
    }


def write_evaluation_md(evaluation: dict) -> str:
    """Render an evaluation result dict as a Markdown document.

    Args:
        evaluation (dict): Output of :func:`evaluate_pipeline_output`.

    Returns:
        str: A complete Markdown document ready to write to a ``.md`` file.
    """
    now      = evaluation["generated_at"]
    repo     = evaluation["repo_name"]
    total    = evaluation["total_score"]
    max_pts  = evaluation["max_score"]
    conf     = evaluation["confidence"]
    sections = evaluation["sections"]
    recs     = evaluation["recommendations"]

    # Confidence badge text
    badge_map = {
        "HIGH":      "✅ HIGH",
        "MEDIUM":    "⚠️ MEDIUM",
        "LOW":       "🔶 LOW",
        "VERY LOW":  "❌ VERY LOW",
    }
    badge = badge_map.get(conf, conf)

    # Progress bar (ASCII, 20 chars wide)
    filled = round(total / max_pts * 20)
    bar    = "█" * filled + "░" * (20 - filled)

    # Section table rows
    section_rows = "\n".join(
        f"| {s['name']} | {s['score']}/{s['max_score']} | "
        f"{_status_icon(s['overall_status'])} {s['overall_status']} |"
        for s in sections
    )

    # Per-section detail blocks
    section_detail = ""
    for s in sections:
        section_detail += f"\n### {s['name']} — {s['score']}/{s['max_score']} pts\n\n"
        section_detail += f"**Status:** {_status_icon(s['overall_status'])} {s['overall_status']}\n\n"
        if s.get("context"):
            section_detail += f"> {s['context']}\n\n"
        section_detail += "| Check | Status | Points | Message |\n"
        section_detail += "|-------|--------|--------|---------|\n"
        for chk in s["checks"]:
            icon = _status_icon(chk["status"])
            section_detail += (
                f"| {chk['name']} | {icon} {chk['status']} | "
                f"+{chk['points_awarded']}/{chk['points_possible']} | "
                f"{chk['message']} |\n"
            )
        if s.get("recommendations"):
            section_detail += "\n**Recommendations:**\n"
            for r in s["recommendations"]:
                section_detail += f"- {r}\n"

    # Recommendations block
    rec_md = (
        "\n".join(f"- {r}" for r in recs)
        if recs else "_No critical issues found._"
    )

    # Confidence explanation
    conf_explain = {
        "HIGH":
            "The pipeline produced high-quality, verifiable outputs across all "
            "sections. Results can be used with high confidence for planning.",
        "MEDIUM":
            "Most outputs are reliable. One or more sections have low signal "
            "(small repo, no API framework detected, etc.). Cross-check "
            "highlighted sections manually.",
        "LOW":
            "Several sections produced weak results. The repo may use patterns "
            "not covered by static analysis, or the file cap excluded key files. "
            "Treat outputs as first-draft estimates only.",
        "VERY LOW":
            "Significant gaps detected across multiple sections. Results should "
            "be treated as rough approximations and validated manually before use.",
    }.get(conf, "")

    md = f"""# {repo} — Pipeline Evaluation Report

> **Auto-generated** by the Reverse Engineer Skill Evaluator · {now}

---

## Overall Score

```
{bar}  {total}/{max_pts} pts
```

**Confidence:** {badge}

{conf_explain}

---

## Section Scores

| Section | Score | Status |
|---------|-------|--------|
{section_rows}
| **TOTAL** | **{total}/{max_pts}** | **{badge}** |

---

## Section Details
{section_detail}

---

## Recommendations

{rec_md}

---

## Interpretation Guide

### What the Scores Mean

| Confidence | Score | Meaning |
|------------|-------|---------|
| HIGH       | ≥ 80  | All key pipeline sections produced verifiable output |
| MEDIUM     | ≥ 60  | Most sections reliable; some manual spot-checks advised |
| LOW        | ≥ 40  | Partial results — likely pattern coverage gaps |
| VERY LOW   | < 40  | Major gaps; treat as rough estimates only |

### Check Statuses

| Status | Meaning |
|--------|---------|
| ✅ PASS | Check passed — result is reliable |
| ⚠️ WARN | Partial or borderline result — review advised |
| ❌ FAIL | Check failed — result in this area may be missing or wrong |

### What Is Reliable vs Heuristic

| Output Area | Reliability | Notes |
|-------------|-------------|-------|
| File count & language distribution | HIGH | Exact filesystem walk |
| Class / method extraction | MEDIUM-HIGH | Regex-based; edge cases exist |
| Import / dependency detection | MEDIUM | Pattern-matched; dynamic imports missed |
| API endpoint extraction | MEDIUM | Attribute/decorator patterns; dynamic routes missed |
| Dead code detection | LOW-MEDIUM | Heuristic only — validate before deleting |
| Entity / DB schema | MEDIUM | ORM annotation & namespace heuristics |
| Microservice boundaries | LOW-MEDIUM | Keyword clustering — AI fallback |
| AI executive summary | HIGH (with API key) | Claude claude-sonnet-4-6; fallback text if no key |
| AI modernization roadmap | HIGH (with API key) | Claude claude-sonnet-4-6; fallback text if no key |

---

## How to Spot-Check Results

### Parsing Quality
- Open the SDD JSON → `module_inventory` array; pick 5 random files
- Verify the `classes` and `methods` lists match the actual source file content

### API Endpoints
- Compare `api_catalog.endpoints` in the SDD JSON against the actual
  controller files in the repository
- Check that HTTP methods (`GET`, `POST`, etc.) are correct

### Dead Code
- Pick 3 files from `dead_code_analysis.unreferenced_files`
- Search the repository for any import or reference to that file
- If found → false positive (this is expected; always validate before deleting)

### Entity Detection
- Open the SDD JSON → `data_architecture.entities`
- Cross-reference entity names against actual ORM model files in the repository

### Dependency Graph
- The Mermaid diagram in the HTML dashboard shows module-to-module edges
- Verify a known dependency exists as an edge in the graph

---

_Generated by Reverse Engineer Skill · Claude Code_
"""
    return md


# ---------------------------------------------------------------------------
# Section evaluators
# ---------------------------------------------------------------------------

def _eval_parsing_quality(parsed, report):
    """Evaluate parsing quality: file coverage, class/method extraction."""
    checks = []
    score  = 0

    # Check 1: At least some files parsed (5 pts)
    total_files = report.get("total_files", 0)
    if total_files >= 10:
        checks.append(_check("Files Parsed", "PASS", 5, 5,
                             f"{total_files} files parsed successfully"))
        score += 5
    elif total_files > 0:
        checks.append(_check("Files Parsed", "WARN", 3, 5,
                             f"Only {total_files} files parsed — repo may be very small or "
                             "only a few file types supported"))
        score += 3
    else:
        checks.append(_check("Files Parsed", "FAIL", 0, 5,
                             "No files parsed — check supported extensions and repo structure"))

    # Check 2: Parse success rate (5 pts)
    total_attempted = len(parsed) + (report.get("skipped", 0) or 0)
    if total_attempted > 0:
        rate = len(parsed) / total_attempted
    else:
        rate = 1.0
    if rate >= 0.90:
        checks.append(_check("Parse Success Rate", "PASS", 5, 5,
                             f"{rate*100:.0f}% of attempted files parsed"))
        score += 5
    elif rate >= 0.70:
        checks.append(_check("Parse Success Rate", "WARN", 3, 5,
                             f"{rate*100:.0f}% parse rate — some files skipped"))
        score += 3
    else:
        checks.append(_check("Parse Success Rate", "FAIL", 0, 5,
                             f"Only {rate*100:.0f}% of files parsed successfully"))

    # Check 3: Classes extracted (5 pts)
    total_classes = report.get("total_classes", 0)
    if total_classes >= 5:
        checks.append(_check("Classes Extracted", "PASS", 5, 5,
                             f"{total_classes} classes identified across parsed files"))
        score += 5
    elif total_classes > 0:
        checks.append(_check("Classes Extracted", "WARN", 2, 5,
                             f"Only {total_classes} classes found — may be a scripting "
                             "language repo or classes use unsupported patterns"))
        score += 2
    else:
        checks.append(_check("Classes Extracted", "FAIL", 0, 5,
                             "0 classes extracted — class detection may need pattern updates"))

    # Check 4: Methods extracted (5 pts)
    total_methods = report.get("total_methods", 0)
    if total_methods >= 10:
        checks.append(_check("Methods Extracted", "PASS", 5, 5,
                             f"{total_methods} methods/functions identified"))
        score += 5
    elif total_methods > 0:
        checks.append(_check("Methods Extracted", "WARN", 2, 5,
                             f"Only {total_methods} methods found"))
        score += 2
    else:
        checks.append(_check("Methods Extracted", "FAIL", 0, 5,
                             "0 methods extracted"))

    recs = []
    if total_classes == 0:
        recs.append("0 classes detected — check parsers.py class regex for "
                    "partial/abstract/sealed modifiers in C# or unusual patterns in the language")
    if total_files < 5:
        recs.append("Very few files parsed — ensure the repo has source files in "
                    "supported extensions (.py, .java, .cs, .ts, .js, .rb, .go, .rs, .php)")

    return _section("1. Parsing Quality", score, 20, checks, recs,
                    context=f"{total_files} files | {total_classes} classes | {total_methods} methods")


def _eval_api_endpoints(endpoints, parsed):
    """Evaluate API endpoint detection quality."""
    checks = []
    score  = 0

    ep_count   = len(endpoints)
    file_count = len(parsed)

    # Check 1: Endpoints found (8 pts)
    if ep_count >= 10:
        checks.append(_check("Endpoints Detected", "PASS", 8, 8,
                             f"{ep_count} API endpoints extracted"))
        score += 8
    elif ep_count > 0:
        checks.append(_check("Endpoints Detected", "WARN", 4, 8,
                             f"Only {ep_count} endpoints detected — repo may have few routes, "
                             "or use dynamic registration patterns"))
        score += 4
    else:
        checks.append(_check("Endpoints Detected", "WARN", 2, 8,
                             "0 endpoints detected. If this is an API server, routes may use "
                             "patterns not covered by static analysis (e.g. reflection, "
                             "attribute-less routing)"))
        score += 2  # Not a hard FAIL — not all repos are API servers

    # Check 2: HTTP methods variety (6 pts)
    if ep_count > 0:
        all_methods = set()
        for ep in endpoints:
            all_methods.update(ep.get("methods", []))
        method_variety = len(all_methods)
        if method_variety >= 3:
            checks.append(_check("HTTP Method Variety", "PASS", 6, 6,
                                 f"Methods detected: {', '.join(sorted(all_methods))}"))
            score += 6
        elif method_variety >= 1:
            checks.append(_check("HTTP Method Variety", "WARN", 3, 6,
                                 f"Only {method_variety} HTTP method type(s) found: "
                                 f"{', '.join(sorted(all_methods))}"))
            score += 3
        else:
            checks.append(_check("HTTP Method Variety", "FAIL", 0, 6,
                                 "No HTTP methods associated with any endpoint"))
    else:
        checks.append(_check("HTTP Method Variety", "WARN", 3, 6,
                             "Cannot assess — no endpoints detected"))
        score += 3

    # Check 3: Path format sanity (6 pts)
    if ep_count > 0:
        valid_paths = sum(
            1 for ep in endpoints
            if ep.get("path") and (ep["path"].startswith("/") or "{" in ep["path"])
        )
        path_rate = valid_paths / ep_count
        if path_rate >= 0.80:
            checks.append(_check("Path Format Validity", "PASS", 6, 6,
                                 f"{valid_paths}/{ep_count} paths have valid route format"))
            score += 6
        elif path_rate >= 0.50:
            checks.append(_check("Path Format Validity", "WARN", 3, 6,
                                 f"Only {valid_paths}/{ep_count} paths look like valid routes"))
            score += 3
        else:
            checks.append(_check("Path Format Validity", "FAIL", 0, 6,
                                 f"Most paths ({ep_count - valid_paths}/{ep_count}) "
                                 "do not match expected route format"))
    else:
        checks.append(_check("Path Format Validity", "WARN", 3, 6,
                             "Cannot assess — no endpoints detected"))
        score += 3

    recs = []
    if ep_count == 0:
        recs.append("No endpoints detected. If this is an API server, check if it uses "
                    "minimal API patterns (e.g. app.MapGet), XML config routing, or "
                    "convention-based routing not captured by attribute scanning")
    if ep_count > 0 and ep_count < 5:
        recs.append(f"Only {ep_count} endpoints found — verify the controller/route files "
                    "were included in the analysis (check file cap and layer allocation)")

    return _section("2. API Endpoint Detection", score, 20, checks, recs,
                    context=f"{ep_count} endpoints extracted from {file_count} files")


def _eval_dead_code(dead_code, report):
    """Evaluate dead code analysis plausibility."""
    checks = []
    score  = 0

    dead_files   = dead_code.get("dead_files", [])
    dead_classes = dead_code.get("dead_classes", [])
    total_files  = report.get("total_files", 1) or 1

    # Check 1: Dead file ratio plausible (5 pts)
    dead_ratio = len(dead_files) / total_files
    if dead_ratio <= 0.50:
        checks.append(_check("Dead File Ratio", "PASS", 5, 5,
                             f"{len(dead_files)} dead files = {dead_ratio*100:.0f}% of total "
                             f"(plausible range)"))
        score += 5
    elif dead_ratio <= 0.80:
        checks.append(_check("Dead File Ratio", "WARN", 2, 5,
                             f"{len(dead_files)} dead files = {dead_ratio*100:.0f}% — "
                             "unusually high; heuristic may over-report in repos with "
                             "many standalone scripts or config files"))
        score += 2
    else:
        checks.append(_check("Dead File Ratio", "FAIL", 0, 5,
                             f"{dead_ratio*100:.0f}% of files flagged as dead — "
                             "heuristic likely unreliable for this repo structure"))

    # Check 2: Analysis ran (produced a result) (5 pts)
    if isinstance(dead_code, dict) and "dead_files" in dead_code:
        checks.append(_check("Analysis Completed", "PASS", 5, 5,
                             "Dead code analysis ran and returned a structured result"))
        score += 5
    else:
        checks.append(_check("Analysis Completed", "FAIL", 0, 5,
                             "Dead code analysis did not return expected data structure"))

    # Check 3: Dead classes detected (5 pts)
    if len(dead_classes) > 0:
        checks.append(_check("Class-Level Analysis", "PASS", 5, 5,
                             f"{len(dead_classes)} potentially unreferenced classes found"))
        score += 5
    elif total_files < 10:
        checks.append(_check("Class-Level Analysis", "WARN", 3, 5,
                             "No dead classes (small repo — expected)"))
        score += 3
    else:
        checks.append(_check("Class-Level Analysis", "WARN", 2, 5,
                             "0 dead classes detected — may indicate all classes "
                             "are referenced, or class-level heuristic needs tuning"))
        score += 2

    recs = []
    if dead_ratio > 0.50:
        recs.append("Dead file ratio is high — the heuristic flags files that are "
                    "never imported by other analyzed files. For script/tool repos this "
                    "is expected. Always validate before deleting flagged files.")
    recs.append("Always manually verify dead code results before deletion — "
                "static analysis cannot detect runtime-loaded modules, "
                "reflection-based usage, or files loaded via config")

    return _section("3. Dead Code Analysis", score, 15, checks, recs,
                    context=f"{len(dead_files)} dead files | {len(dead_classes)} dead classes")


def _eval_data_architecture(db_schema, data_boundaries, parsed):
    """Evaluate database schema and microservice boundary detection."""
    checks = []
    score  = 0

    schema      = db_schema or {}
    boundaries  = data_boundaries or []
    entity_count = schema.get("entity_count", 0)
    rel_count    = schema.get("relationship_count", 0)

    # Detect what ORM the repo likely uses (for context)
    langs = set(f.get("language", "") for f in parsed)
    expected_orm = (
        "EF Core (C#)" if "csharp" in langs else
        "JPA/Hibernate (Java)" if "java" in langs else
        "SQLAlchemy/Django (Python)" if "python" in langs else
        "unknown ORM"
    )

    # Check 1: Entities detected (7 pts)
    if entity_count >= 5:
        checks.append(_check("Entities Detected", "PASS", 7, 7,
                             f"{entity_count} data entities extracted"))
        score += 7
    elif entity_count > 0:
        checks.append(_check("Entities Detected", "WARN", 4, 7,
                             f"Only {entity_count} entities found — domain model files may "
                             "have been excluded by the file cap, or ORM patterns differ "
                             f"from expected ({expected_orm})"))
        score += 4
    else:
        checks.append(_check("Entities Detected", "WARN", 2, 7,
                             f"0 entities detected. If repo uses {expected_orm}, check that "
                             "domain/entity files are in the analyzed set and use standard "
                             "ORM annotations or namespace conventions"))
        score += 2  # Not a hard FAIL — some repos have no ORM

    # Check 2: Microservice boundaries identified (5 pts)
    if len(boundaries) >= 3:
        checks.append(_check("Microservice Boundaries", "PASS", 5, 5,
                             f"{len(boundaries)} bounded contexts identified"))
        score += 5
    elif len(boundaries) > 0:
        checks.append(_check("Microservice Boundaries", "WARN", 3, 5,
                             f"Only {len(boundaries)} boundary/boundaries found — "
                             "entity clustering may benefit from more domain files"))
        score += 3
    else:
        checks.append(_check("Microservice Boundaries", "FAIL", 0, 5,
                             "No microservice boundaries identified — no entities or AI "
                             "roadmap to derive boundaries from"))

    # Check 3: Relationship detection (3 pts)
    if rel_count > 0:
        checks.append(_check("Relationships Detected", "PASS", 3, 3,
                             f"{rel_count} inter-entity relationships mapped"))
        score += 3
    elif entity_count > 0:
        checks.append(_check("Relationships Detected", "WARN", 1, 3,
                             f"0 relationships detected despite {entity_count} entities. "
                             "Repo may use Fluent API or private backing fields for "
                             "navigation properties (not captured by regex analysis)"))
        score += 1
    else:
        checks.append(_check("Relationships Detected", "WARN", 1, 3,
                             "Cannot assess — no entities detected"))
        score += 1

    recs = []
    if entity_count == 0:
        recs.append("No entities detected. Ensure domain/model/entity files are "
                    "within the 300-file cap — increase the layer-3 quota in SLOTS "
                    f"dict in pipeline.py if needed. Expected ORM: {expected_orm}")
    if rel_count == 0 and entity_count > 0:
        recs.append("0 relationships detected — if the repo uses EF Core Fluent API "
                    "or JPA XML mapping, relationships won't be found by regex. "
                    "Consider enhancing _extract_db_entities_dotnet() to parse "
                    "OnModelCreating() method bodies")

    return _section("4. Entity / Data Architecture", score, 15, checks, recs,
                    context=(
                        f"{entity_count} entities | {rel_count} relationships | "
                        f"{len(boundaries)} bounded contexts"
                    ))


def _eval_dependency_graph(dep_map, graphviz_code, tech_stack):
    """Evaluate dependency graph and tech stack detection."""
    checks = []
    score  = 0

    dep_node_count = len(dep_map)
    dep_edge_count = sum(len(v) for v in dep_map.values())

    # Check 1: Dependency map populated (5 pts)
    if dep_node_count >= 5:
        checks.append(_check("Dependency Map Built", "PASS", 5, 5,
                             f"{dep_node_count} modules with {dep_edge_count} dependency edges"))
        score += 5
    elif dep_node_count > 0:
        checks.append(_check("Dependency Map Built", "WARN", 3, 5,
                             f"Only {dep_node_count} modules in dependency map — "
                             "small repo or import extraction limited"))
        score += 3
    else:
        checks.append(_check("Dependency Map Built", "FAIL", 0, 5,
                             "Dependency map is empty — import detection may have failed"))

    # Check 2: Graphviz diagram generated (5 pts)
    if graphviz_code and len(graphviz_code.strip()) > 20:
        node_count_in_diagram = graphviz_code.count("->")
        checks.append(_check("Graphviz Diagram", "PASS", 5, 5,
                             f"Graphviz diagram generated ({node_count_in_diagram} edges shown)"))
        score += 5
    elif graphviz_code:
        checks.append(_check("Graphviz Diagram", "WARN", 2, 5,
                             "Graphviz diagram generated but very small — "
                             "few inter-module dependencies detected"))
        score += 2
    else:
        checks.append(_check("Graphviz Diagram", "FAIL", 0, 5,
                             "No Graphviz diagram generated"))

    # Check 3: Tech stack detected (5 pts)
    if len(tech_stack) >= 3:
        checks.append(_check("Tech Stack Detection", "PASS", 5, 5,
                             f"{len(tech_stack)} technologies identified: "
                             f"{', '.join(tech_stack[:5])}"))
        score += 5
    elif len(tech_stack) > 0:
        checks.append(_check("Tech Stack Detection", "WARN", 3, 5,
                             f"Only {len(tech_stack)} technology/technologies detected: "
                             f"{', '.join(tech_stack)}"))
        score += 3
    else:
        checks.append(_check("Tech Stack Detection", "FAIL", 0, 5,
                             "No tech stack items detected — "
                             "dependency files (package.json, .csproj, pom.xml) may be missing"))

    recs = []
    if dep_node_count == 0:
        recs.append("Dependency map empty — check that import/using statement "
                    "patterns in parsers.py cover the repo's language")
    if len(tech_stack) == 0:
        recs.append("Tech stack detection failed — ensure package manager files "
                    "(package.json, *.csproj, pom.xml, requirements.txt) are present "
                    "in the repo root")

    return _section("5. Dependency Graph", score, 15, checks, recs,
                    context=(
                        f"{dep_node_count} dep nodes | {dep_edge_count} edges | "
                        f"{len(tech_stack)} tech items"
                    ))


def _eval_ai_analysis(summary, modernization):
    """Evaluate AI analysis quality and completeness."""
    checks = []
    score  = 0

    # Fallback sentinel text that appears when there's no API key
    FALLBACK_SIGNALS = [
        "set anthropic_api_key",
        "ai summary not available",
        "full ai reasoning unavailable",
        "fallback",
    ]

    def _is_fallback(text):
        return any(s in text.lower() for s in FALLBACK_SIGNALS)

    purpose_text = summary.get("purpose", "")
    arch_pattern = summary.get("architecture_pattern", "")
    priority     = summary.get("modernization_priority", "")
    phases       = modernization.get("phases", [])
    target_stack = modernization.get("target_stack", [])
    effort       = modernization.get("estimated_total_effort", "")

    # Check 1: Executive summary populated (5 pts)
    if purpose_text and not _is_fallback(purpose_text) and len(purpose_text) > 50:
        checks.append(_check("Executive Summary", "PASS", 5, 5,
                             "AI-generated executive summary present and substantive"))
        score += 5
    elif purpose_text and _is_fallback(purpose_text):
        checks.append(_check("Executive Summary", "WARN", 2, 5,
                             "Fallback text in place — set ANTHROPIC_API_KEY for "
                             "AI-generated summary"))
        score += 2
    elif purpose_text:
        checks.append(_check("Executive Summary", "WARN", 3, 5,
                             "Summary present but brief — may be heuristic fallback"))
        score += 3
    else:
        checks.append(_check("Executive Summary", "FAIL", 0, 5,
                             "No executive summary generated"))

    # Check 2: Architecture pattern identified (5 pts)
    known_patterns = [
        "monolith", "microservic", "mvc", "mvvm", "layered",
        "hexagonal", "clean architecture", "cqrs", "event-driven",
        "domain-driven", "service-oriented", "serverless",
    ]
    if arch_pattern and any(p in arch_pattern.lower() for p in known_patterns):
        checks.append(_check("Architecture Pattern", "PASS", 5, 5,
                             f"Pattern identified: '{arch_pattern}'"))
        score += 5
    elif arch_pattern:
        checks.append(_check("Architecture Pattern", "WARN", 3, 5,
                             f"Pattern set to '{arch_pattern}' — verify against actual structure"))
        score += 3
    else:
        checks.append(_check("Architecture Pattern", "FAIL", 0, 5,
                             "No architecture pattern identified"))

    # Check 3: Modernization roadmap has phases (5 pts)
    if len(phases) >= 3:
        phase_titles = [p.get("title", "") for p in phases]
        checks.append(_check("Modernization Phases", "PASS", 5, 5,
                             f"{len(phases)} phases: {', '.join(phase_titles[:3])}..."))
        score += 5
    elif len(phases) > 0:
        checks.append(_check("Modernization Phases", "WARN", 3, 5,
                             f"Only {len(phases)} phase(s) in roadmap — "
                             "may be fallback content"))
        score += 3
    else:
        checks.append(_check("Modernization Phases", "FAIL", 0, 5,
                             "No modernization phases generated — "
                             "check AI API key or roadmap fallback logic"))

    recs = []
    if any(_is_fallback(t) for t in [purpose_text, str(target_stack), effort]):
        recs.append("Set ANTHROPIC_API_KEY environment variable to get full AI-powered "
                    "executive summary and modernization roadmap instead of fallback text")
    if len(phases) == 0:
        recs.append("Modernization roadmap has no phases — AI analysis may have failed. "
                    "Check logs for ANTHROPIC_API_KEY errors or API timeout issues")

    ai_status = (
        "AI-powered (Claude claude-sonnet-4-6)"
        if not _is_fallback(purpose_text)
        else "Heuristic fallback (no API key)"
    )

    return _section("6. AI Analysis Quality", score, 15, checks, recs,
                    context=f"{ai_status} | {len(phases)} roadmap phases | target: {', '.join(target_stack[:3]) or 'N/A'}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check(name, status, points_awarded, points_possible, message):
    """Build a single check result dict."""
    return {
        "name":             name,
        "status":           status,   # "PASS" | "WARN" | "FAIL"
        "points_awarded":   points_awarded,
        "points_possible":  points_possible,
        "message":          message,
    }


def _section(name, score, max_score, checks, recommendations=None, context=""):
    """Build a section result dict."""
    # Overall section status = worst check status
    statuses = [c["status"] for c in checks]
    overall  = (
        "FAIL" if "FAIL" in statuses else
        "WARN" if "WARN" in statuses else
        "PASS"
    )
    return {
        "name":            name,
        "score":           score,
        "max_score":       max_score,
        "overall_status":  overall,
        "checks":          checks,
        "recommendations": recommendations or [],
        "context":         context,
    }


def _status_icon(status):
    return {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(status, "")


def _build_summary_lines(sections, total, confidence, repo_name):
    """Build a list of console-friendly summary lines."""
    lines = [
        f"  Evaluation Score  : {total}/100 pts  [{confidence} confidence]",
    ]
    for s in sections:
        icon = _status_icon(s["overall_status"])
        lines.append(
            f"     {icon} {s['name']:<35} {s['score']:>2}/{s['max_score']} pts"
        )
    return lines


def _collect_recommendations(sections):
    """Flatten all section recommendations into a single list, deduped."""
    seen = set()
    recs = []
    for s in sections:
        for r in s.get("recommendations", []):
            if r not in seen:
                seen.add(r)
                recs.append(r)
    return recs
