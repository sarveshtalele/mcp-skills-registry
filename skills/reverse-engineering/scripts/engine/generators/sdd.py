"""
SDD JSON Generator
==================
Produces a System Design Document (SDD) in JSON format that encapsulates
every artefact produced by the reverse engineering pipeline: codebase
metrics, architecture layers, module inventory, API catalog, dependency
analysis, dead code analysis, modernisation roadmap, risk assessment, and
tech-debt inventory.

The SDD schema is versioned (currently ``SDD-Framework-v1``) and includes a
``sdd_metadata`` block with generation timestamp and generator attribution so
that consumers can track provenance.
"""

import datetime
from pathlib import Path

from engine.analyzer import (
    detect_platform,
    detect_architecture_layers,
    find_top_modules,
    extract_external_deps,
)


def generate_sdd(
    repo_name,
    repo_url,
    parsed,
    report,
    dep_map,
    endpoints,
    openapi_spec,
    dead_code,
    graphviz_code,
    tech_stack,
    summary,
    modernization,
    repo_path,
    db_schema=None,
    data_boundaries=None,
    business_logic=None,
    block_diagram=None,
    auth_analysis=None,
    screens_nav=None,
):
    """Build and return the complete SDD data structure for a repository.

    Args:
        repo_name (str): Human-readable repository name.
        repo_url (str): Original GitHub clone URL.
        parsed (list[dict]): List of file records from
            :func:`engine.parsers.parse_file`.
        report (dict): Metrics dict from
            :func:`engine.analyzer.generate_report`.
        dep_map (dict[str, set[str]]): Module dependency map from
            :func:`engine.analyzer.build_dependency_map`.
        endpoints (list[dict]): API endpoint records from
            :func:`engine.analyzer.extract_api_endpoints`.
        openapi_spec (dict): OpenAPI 3.0 spec from
            :func:`engine.analyzer.generate_openapi_spec`.
        dead_code (dict): Dead-code report from
            :func:`engine.analyzer.detect_dead_code`.
        mermaid_code (str): Mermaid diagram string from
            :func:`engine.analyzer.generate_mermaid`.
        tech_stack (list[str]): Detected technologies from
            :func:`engine.analyzer.detect_tech_stack`.
        summary (dict): AI executive summary from
            :func:`engine.ai_analysis.ai_executive_summary`.
        modernization (dict): AI modernisation roadmap from
            :func:`engine.ai_analysis.ai_modernization_roadmap`.
        repo_path (str): Absolute path to the cloned repository root
            (passed through to helpers that need filesystem access).

    Returns:
        dict: A fully populated SDD document ready for JSON serialisation.
        The top-level keys are:

        - ``"sdd_metadata"``
        - ``"project"``
        - ``"executive_summary"``
        - ``"codebase_metrics"``
        - ``"architecture"``
        - ``"module_inventory"``
        - ``"api_catalog"``
        - ``"dependency_analysis"``
        - ``"dead_code_analysis"``
        - ``"business_logic"``
        - ``"modernization_roadmap"``
        - ``"risk_assessment"``
        - ``"tech_debt_inventory"``
    """
    top_mods = find_top_modules(dep_map)

    # Build component list (unique classes across all files, capped at 60).
    components = []
    seen_cls = set()
    for item in parsed:
        for cls in item.get("classes", []):
            if cls not in seen_cls:
                seen_cls.add(cls)
                components.append({
                    "name": cls,
                    "type": "Class",
                    "file": Path(item["file"]).name,
                    "methods_count": len(item.get("methods", [])),
                })

    sdd = {
        "sdd_metadata": {
            "version": "1.0",
            "schema": "SDD-Framework-v1",
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
            "generator": "Reverse Engineer Skill — Claude Code",
            "model_used": "claude-sonnet-4-6",
        },
        "project": {
            "name": repo_name,
            "repository_url": repo_url,
            "primary_language": (
                max(report["languages"], key=report["languages"].get)
                if report["languages"]
                else "unknown"
            ),
            "tech_stack": tech_stack,
            "platform": detect_platform(parsed),
            "architecture_layers": detect_architecture_layers(parsed),
        },
        "executive_summary": {
            "purpose": summary.get("purpose", ""),
            "architecture_pattern": summary.get("architecture_pattern", "Monolithic"),
            "tech_debt_concerns": summary.get("tech_debt_concerns", []),
            "modernization_priority": summary.get("modernization_priority", "HIGH"),
            "priority_reasoning": summary.get("priority_reasoning", ""),
        },
        "codebase_metrics": {
            "total_files_analyzed": report["total_files"],
            "total_classes": report["total_classes"],
            "total_methods": report["total_methods"],
            "total_api_endpoints": len(endpoints),
            "language_distribution": report["languages"],
            "most_connected_modules": [
                {"module": m, "connections": c} for m, c in top_mods
            ],
            "dead_code_files": len(dead_code.get("dead_files", [])),
            "dead_code_classes": len(dead_code.get("dead_classes", [])),
        },
        "architecture": {
            "style": summary.get("architecture_pattern", "Monolithic"),
            "layers": detect_architecture_layers(parsed),
            "components": components[:60],
            "dependency_graph": {
                "format": "Graphviz",
                "diagram": graphviz_code,
            },
        },
        "module_inventory": [
            {
                "file": item["file"],
                "relative_path": str(Path(item["file"]).name),
                "language": item.get("language"),
                "namespace": item.get("namespace", item.get("package", "")),
                "classes": item.get("classes", []),
                "methods": item.get("methods", [])[:30],
                "dependencies": item.get("dependencies", []),
                "api_routes": item.get("routes", []),
            }
            for item in parsed
        ],
        "api_catalog": {
            "openapi_spec": openapi_spec,
            "total_endpoints": len(endpoints),
            "endpoints": [
                {
                    "path": ep["path"],
                    "http_methods": ep["methods"],
                    "handler": (
                        f"{ep.get('class') or 'global'}"
                        f".{ep.get('method') or 'handler'}()"
                    ),
                    "file": Path(ep["file"]).name,
                }
                for ep in endpoints
            ],
        },
        "dependency_analysis": {
            "total_unique_external_deps": len(extract_external_deps(parsed)),
            "external_dependencies": extract_external_deps(parsed),
            "dependency_map_sample": {
                k: sorted(list(v))[:10]
                for k, v in list(dep_map.items())[:25]
            },
            "top_10_most_connected": [
                {"module": m, "connections": c} for m, c in top_mods
            ],
        },
        "dead_code_analysis": {
            "summary": (
                f"{len(dead_code.get('dead_files', []))} potentially unreferenced files, "
                f"{len(dead_code.get('dead_classes', []))} unreferenced classes"
            ),
            "unreferenced_files": [
                Path(f).name for f in dead_code.get("dead_files", [])
            ],
            "unreferenced_files_full_paths": dead_code.get("dead_files", []),
            "unreferenced_classes": dead_code.get("dead_classes", [])[:30],
        },
        "data_architecture": {
            "entity_count":       (db_schema or {}).get("entity_count", 0),
            "relationship_count": (db_schema or {}).get("relationship_count", 0),
            "has_schema":         (db_schema or {}).get("has_schema", False),
            "entities": [
                {
                    "name":          ent.get("name", ""),
                    "table":         ent.get("table", ""),
                    "fields":        ent.get("fields", []),
                    "relationships": ent.get("relationships", []),
                    "file":          Path(ent.get("file", "")).name,
                }
                for ent in (db_schema or {}).get("entities", [])
            ],
            "microservice_data_boundaries": data_boundaries or [],
            "migration_notes": (
                "Each bounded context (microservice) should own its own database. "
                "Shared tables must be decomposed via API contracts or event-driven "
                "integration (e.g., domain events with an outbox pattern). "
                "Begin with the least-coupled bounded context to minimise risk."
            ),
        },
        "business_logic": {
            "business_domain":          (business_logic or {}).get("business_domain", ""),
            "what_it_does":             (business_logic or {}).get("what_it_does", ""),
            "core_workflows":           (business_logic or {}).get("core_workflows", []),
            "user_roles":               (business_logic or {}).get("user_roles", []),
            "key_business_rules":       (business_logic or {}).get("key_business_rules", []),
            "data_entities_explained":  (business_logic or {}).get("data_entities_explained", []),
            "integrations":             (business_logic or {}).get("integrations", []),
            "ai_generated":             not (business_logic or {}).get("fallback_used", True),
            "block_diagram":            block_diagram or "",
        },
        "modernization_roadmap": modernization,
        "risk_assessment": [
            {
                "id": "RISK-001",
                "category": "Technical Debt",
                "severity": "HIGH" if report["total_files"] > 50 else "MEDIUM",
                "description": (
                    f"Codebase contains {report['total_files']} files with accumulated tech debt."
                ),
                "recommendation": (
                    "Conduct systematic code review and establish refactoring backlog."
                ),
            },
            {
                "id": "RISK-002",
                "category": "Dead Code",
                "severity": (
                    "MEDIUM" if len(dead_code.get("dead_files", [])) > 5 else "LOW"
                ),
                "description": (
                    f"{len(dead_code.get('dead_files', []))} potentially unreferenced "
                    "modules detected."
                ),
                "recommendation": (
                    "Review and prune unused code to reduce maintenance surface area."
                ),
            },
            {
                "id": "RISK-003",
                "category": "API Documentation",
                "severity": "HIGH" if len(endpoints) == 0 else "LOW",
                "description": (
                    f"{len(endpoints)} API endpoints extracted. "
                    + (
                        "No routes detected — full documentation required."
                        if not endpoints
                        else "Partial auto-extraction completed."
                    )
                ),
                "recommendation": (
                    "Ensure all API contracts are documented with OpenAPI 3.0 specification."
                ),
            },
            {
                "id": "RISK-004",
                "category": "Dependency Hygiene",
                "severity": "MEDIUM",
                "description": (
                    f"{len(extract_external_deps(parsed))} unique external dependencies detected."
                ),
                "recommendation": (
                    "Audit dependency versions against CVE databases and upgrade stale packages."
                ),
            },
        ],
        "tech_debt_inventory": [
            {
                "category": issue,
                "severity": "HIGH",
                "description": desc,
            }
            for issue, desc in [
                (
                    "Legacy Dependencies",
                    f"Detected {len(extract_external_deps(parsed))} external dependencies "
                    "— audit for outdated versions.",
                ),
                (
                    "Documentation Coverage",
                    "Auto-documentation generated; manual review recommended for accuracy.",
                ),
                (
                    "Test Coverage",
                    "Test coverage metrics not assessed — review existing test suites.",
                ),
                (
                    "Dead Code Removal",
                    f"{len(dead_code.get('dead_files', []))} unreferenced files identified "
                    "for potential removal.",
                ),
                (
                    "API Contract Gaps",
                    (
                        "Full API documentation missing."
                        if not endpoints
                        else f"{len(endpoints)} endpoints extracted; validate completeness."
                    ),
                ),
            ]
        ],
        "auth_analysis": {
            "auth_type":          (auth_analysis or {}).get("auth_type", "Not analyzed"),
            "auth_frameworks":    (auth_analysis or {}).get("auth_frameworks", []),
            "rbac":               (auth_analysis or {}).get("rbac", []),
            "abac":               (auth_analysis or {}).get("abac", []),
            "rebac":              (auth_analysis or {}).get("rebac", []),
            "roles_detected":     (auth_analysis or {}).get("roles_detected", []),
            "policies_detected":  (auth_analysis or {}).get("policies_detected", []),
            "protected_routes":   (auth_analysis or {}).get("protected_routes", []),
            "public_routes":      (auth_analysis or {}).get("public_routes", []),
        },
        "screens_navigation": {
            "project_type":     (screens_nav or {}).get("project_type", "Web Application"),
            "screen_count":     (screens_nav or {}).get("screen_count", 0),
            "screens":          (screens_nav or {}).get("screens", []),
            "navigation_flow":  (screens_nav or {}).get("navigation_flow", []),
        },
    }
    return sdd
