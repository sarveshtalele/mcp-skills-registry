"""
Markdown Report Generator
=========================
Produces a focused, stakeholder-ready Markdown report with four sections:

1. System Design Overview — complete architectural picture of the project
2. Authentication & Access Control — RBAC / ABAC / ReBAC analysis
3. Business Logic Extractor — domain workflows, rules, entities
4. Screen-by-Screen Navigation — end-to-end user journey through the UI

The report is self-contained and renders in any GFM-compatible viewer
(GitHub, GitLab, Obsidian, Typora, VS Code Preview).
"""

import json
import datetime
from pathlib import Path

from engine.analyzer import (
    detect_platform,
    detect_architecture_layers,
    extract_external_deps,
)


def render_ascii_block_diagram(block_diagram_data):
    if not block_diagram_data or not isinstance(block_diagram_data, dict) or "layers" not in block_diagram_data:
        return "No system architecture block diagram available."

    lines = []
    box_width = 72
    inner_width = box_width - 2

    layers = block_diagram_data.get("layers", [])
    edges = block_diagram_data.get("edges", [])

    for idx, layer in enumerate(layers):
        lines.append("┌" + "─" * inner_width + "┐")
        title = f" {layer.get('label', 'Layer').upper()} "
        lines.append("│" + title.center(inner_width, " ") + "│")
        lines.append("├" + "─" * inner_width + "┤")

        nodes = layer.get("nodes", [])
        if not nodes:
            lines.append("│" + " (No components detected) ".center(inner_width) + "│")
        else:
            node_labels = [f"• {n.get('label', '')}" for n in nodes]
            row = []
            for i, label in enumerate(node_labels):
                row.append(label)
                if len(row) == 2 or i == len(node_labels) - 1:
                    if len(row) == 2:
                        col_width = inner_width // 2
                        left_part = row[0].ljust(col_width - 2)
                        right_part = row[1].ljust(inner_width - len(left_part) - 4)
                        lines.append(f"│  {left_part}  {right_part}  │")
                    else:
                        lines.append(f"│  {row[0].ljust(inner_width - 4)}  │")
                    row = []

        lines.append("└" + "─" * inner_width + "┘")

        if idx < len(layers) - 1:
            current_node_ids = {n["id"] for n in nodes}
            next_nodes = layers[idx + 1].get("nodes", [])
            next_node_ids = {n["id"] for n in next_nodes}
            layer_edge_labels = []
            for edge in edges:
                if edge.get("from") in current_node_ids and edge.get("to") in next_node_ids:
                    lbl = edge.get("label", "")
                    if lbl and lbl not in layer_edge_labels:
                        layer_edge_labels.append(lbl)
            connector_label = f" ({', '.join(layer_edge_labels)})" if layer_edge_labels else ""
            lines.append(" ")
            lines.append("│".center(box_width).rstrip() + connector_label)
            lines.append("▼".center(box_width).rstrip())
            lines.append(" ")

    return "\n".join(lines)


def generate_md_report(
    repo_name,
    repo_url,
    report,
    parsed,
    dep_map,
    endpoints,
    openapi_spec,
    dead_code,
    tech_stack,
    summary,
    modernization,
    top_mods,
    db_schema=None,
    data_boundaries=None,
    business_logic=None,
    block_diagram=None,
    auth_analysis=None,
    screens_nav=None,
):
    """Build the focused 4-section Markdown report.

    Sections:
    1. System Design Overview
    2. Authentication & Access Control (RBAC / ABAC / ReBAC)
    3. Business Logic Extractor
    4. Screen-by-Screen Navigation

    Returns:
        str: Complete Markdown document.
    """
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    primary = (
        max(report["languages"], key=report["languages"].get)
        if report["languages"] else "unknown"
    )

    tech_stack_str = (
        ", ".join(f"`{t}`" for t in tech_stack) if tech_stack else "_None detected_"
    )

    # ------------------------------------------------------------------
    # Section 1 helpers — System Design Overview
    # ------------------------------------------------------------------
    lang_rows = "\n".join(
        f"| {lang.capitalize()} | {count} | "
        f"{round(count / report['total_files'] * 100 if report['total_files'] else 0)}% |"
        for lang, count in sorted(
            report["languages"].items(), key=lambda x: x[1], reverse=True
        )
    )

    arch_layers_md = "\n".join(
        f"- {layer}" for layer in detect_architecture_layers(parsed)
    ) or "- _No distinct layers detected_"

    ascii_diagram = render_ascii_block_diagram(block_diagram) if isinstance(block_diagram, dict) else "No visual diagram available."

    # Dependency top modules
    top_deps_md = "\n".join(
        f"| `{m}` | {c} |" for m, c in top_mods[:10]
    ) or "| _No data_ | — |"

    ext_dep_count = len(extract_external_deps(parsed))

    # SDD metrics table
    db_s = db_schema or {}
    concerns_md = "\n".join(f"- {c}" for c in summary.get("tech_debt_concerns", []))
    phases_md = ""
    for ph in modernization.get("phases", []):
        tasks_md = "\n".join(f"  - {t}" for t in ph.get("tasks", []))
        phases_md += (
            f"\n**Phase {ph.get('phase')}: {ph.get('title')}** "
            f"`{ph.get('risk','')} risk` — _{ph.get('duration')}_\n{tasks_md}\n"
        )
    microservices_md = "\n".join(
        f"- **{s}**" for s in modernization.get("microservices_boundaries", [])
    ) or "- _Analysis pending_"
    target_stack_str = (
        ", ".join(f"`{t}`" for t in modernization.get("target_stack", []))
        or "_See modernization plan_"
    )
    risk_factors_md = "\n".join(f"- {r}" for r in modernization.get("risk_factors", []))

    # ------------------------------------------------------------------
    # Section 2 helpers — Authentication & Access Control
    # ------------------------------------------------------------------
    auth = auth_analysis or {}
    auth_type = auth.get("auth_type", "No structured authorization detected")
    auth_frameworks_md = "\n".join(
        f"- `{f}`" for f in auth.get("auth_frameworks", [])
    ) or "- _None detected_"

    roles_md = ", ".join(f"`{r}`" for r in auth.get("roles_detected", [])) or "_None detected_"
    policies_md = ", ".join(f"`{p}`" for p in auth.get("policies_detected", [])) or "_None detected_"

    def _auth_table(findings, label):
        if not findings:
            return f"_No {label} patterns detected._"
        rows = "\n".join(
            f"| `{f['file']}` | {f['pattern']} | {f.get('example','')[:50]} |"
            for f in findings[:15]
        )
        return (
            "| File | Pattern | Example |\n"
            "|------|---------|----------|\n"
            + rows
        )

    rbac_table  = _auth_table(auth.get("rbac", []),  "RBAC")
    abac_table  = _auth_table(auth.get("abac", []),  "ABAC")
    rebac_table = _auth_table(auth.get("rebac", []), "ReBAC")

    protected_routes_md = "\n".join(
        f"- `{r}`" for r in auth.get("protected_routes", [])[:20]
    ) or "- _None detected_"
    public_routes_md = "\n".join(
        f"- `{r}`" for r in auth.get("public_routes", [])[:20]
    ) or "- _None detected_"

    # ------------------------------------------------------------------
    # Section 3 helpers — Business Logic Extractor
    # ------------------------------------------------------------------
    bl = business_logic or {}
    bl_domain   = bl.get("business_domain", "General Business Application")
    bl_what     = bl.get("what_it_does", "_Business logic analysis unavailable._")
    bl_roles    = bl.get("user_roles", [])
    bl_rules    = bl.get("key_business_rules", [])
    bl_workflows = bl.get("core_workflows", [])
    bl_entities  = bl.get("data_entities_explained", [])
    bl_integrations = bl.get("integrations", [])

    bl_roles_md = "\n".join(f"- **{r}**" for r in bl_roles) or "_No roles detected_"
    bl_rules_md = "\n".join(f"- {rule}" for rule in bl_rules) or "_No business rules inferred_"
    bl_integrations_md = "\n".join(f"- `{i}`" for i in bl_integrations) or "_None detected_"

    bl_workflows_md = ""
    for wf in bl_workflows:
        steps_md = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(wf.get("steps", [])))
        eps_md = ", ".join(f"`{e}`" for e in wf.get("endpoints", [])) or "_N/A_"
        bl_workflows_md += (
            f"\n#### {wf.get('name', 'Workflow')}\n"
            f"{wf.get('description', '')}\n\n"
            f"**Steps:**\n{steps_md}\n\n"
            f"**Key endpoints:** {eps_md}\n"
        )
    if not bl_workflows_md:
        bl_workflows_md = "_No workflows inferred from API structure._"

    if bl_entities:
        entity_rows = "\n".join(
            f"| `{e.get('entity','')}` | {e.get('business_meaning','')} | "
            f"{', '.join(e.get('key_operations', [])[:3])} |"
            for e in bl_entities
        )
        bl_entities_md = (
            "| Entity | Business Meaning | Key Operations |\n"
            "|--------|-----------------|----------------|\n"
            + entity_rows
        )
    else:
        bl_entities_md = "_No entity definitions detected in analyzed files._"

    # Data architecture entities
    db_entities_md = ""
    if db_s.get("entities"):
        rows = "\n".join(
            f"| `{e.get('name','')}` | `{e.get('table','')}` | "
            f"{len(e.get('fields',[]))} | {len(e.get('relationships',[]))} |"
            for e in db_s.get("entities", [])
        )
        db_entities_md = (
            "| Entity | Table | Fields | Relationships |\n"
            "|--------|-------|--------|---------------|\n"
            + rows
        )
    else:
        db_entities_md = "_No entity definitions detected._"

    # Microservice boundaries
    boundaries_md = ""
    for b in (data_boundaries or []):
        ents = ", ".join(f"`{e}`" for e in b["entities"]) if b["entities"] else "_From AI roadmap_"
        boundaries_md += f"\n#### {b['name']}\n- Entities: {ents}\n"
    if not boundaries_md:
        boundaries_md = "_No data boundaries identified._"

    # API catalog
    if endpoints:
        api_rows = "\n".join(
            f"| `{', '.join(ep['methods'])}` | `{ep['path']}` | "
            f"`{ep.get('class') or 'global'}.{ep.get('method') or 'handler'}()` | "
            f"`{Path(ep['file']).name}` |"
            for ep in endpoints[:50]
        )
        api_table = (
            "| Method | Path | Handler | File |\n"
            "|--------|------|---------|------|\n"
            + api_rows
        )
        if len(endpoints) > 50:
            api_table += f"\n\n_...and {len(endpoints) - 50} more endpoints._"
    else:
        api_table = "_No API routes detected via static analysis._"

    # ------------------------------------------------------------------
    # Section 4 helpers — Screen-by-Screen Navigation
    # ------------------------------------------------------------------
    nav = screens_nav or {}
    project_type = nav.get("project_type", "Web Application")
    screens = nav.get("screens", [])
    nav_flow = nav.get("navigation_flow", [])

    screens_md = ""
    for s in screens:
        routes_str = ", ".join(f"`{r}`" for r in s.get("routes", [])) or "_Inferred from controller_"
        classes_str = ", ".join(f"`{c}`" for c in s.get("classes", [])) or "_N/A_"
        screens_md += (
            f"\n#### {s['name']}\n"
            f"- **Type:** {s['type']}\n"
            f"- **File:** `{s['file']}`\n"
            f"- **Description:** {s['description']}\n"
            f"- **Routes/Paths:** {routes_str}\n"
            f"- **Classes:** {classes_str}\n"
        )
    if not screens_md:
        screens_md = "_No distinct screens detected. This may be an API-only service._"

    # Navigation flow as an ASCII flow
    nav_flow_md = ""
    if nav_flow:
        for edge in nav_flow[:20]:
            nav_flow_md += f"- **{edge['from']}** → **{edge['to']}** _{edge['label']}_\n"
    else:
        nav_flow_md = "_Navigation flow inferred from route/controller analysis._\n"

    # Build Mermaid flowchart for screen navigation
    if nav_flow:
        mermaid_nodes = set()
        mermaid_lines = []
        for edge in nav_flow[:15]:
            src = edge["from"].replace(" ", "_").replace("-", "_")
            tgt = edge["to"].replace(" ", "_").replace("-", "_")
            lbl = edge["label"]
            mermaid_nodes.add((src, edge["from"]))
            mermaid_nodes.add((tgt, edge["to"]))
            mermaid_lines.append(f'  {src} -->|"{lbl}"| {tgt}')
        node_defs = "\n".join(f'  {nid}["{nlabel}"]' for nid, nlabel in sorted(mermaid_nodes))
        mermaid_nav = "```mermaid\nflowchart TD\n" + node_defs + "\n" + "\n".join(mermaid_lines) + "\n```"
    else:
        mermaid_nav = "_No navigation flow detected._"

    # ------------------------------------------------------------------
    # Assemble report
    # ------------------------------------------------------------------
    report_md = f"""# {repo_name} — Reverse Engineering Report

> **Auto-generated** by the Reverse Engineer Skill · {now}
> Repository: [{repo_url}]({repo_url})
> Primary Language: **{primary.capitalize()}**  |  Project Type: **{project_type}**
> Analysis Engine: **Pure static heuristics — no API keys required**

---

## Table of Contents

1. [System Design Overview](#1-system-design-overview)
2. [Authentication & Access Control](#2-authentication--access-control)
3. [Business Logic Extractor](#3-business-logic-extractor)
4. [Screen-by-Screen Navigation](#4-screen-by-screen-navigation)

---

## 1. System Design Overview

> Complete architectural picture of `{repo_name}` — how the system is built,
> what it uses, and how its parts connect.

### 1.1 Executive Summary

{summary.get('purpose', '_Summary not available._')}

| Attribute | Value |
|-----------|-------|
| **Architecture Pattern** | {summary.get('architecture_pattern', 'Monolithic')} |
| **Modernization Priority** | {summary.get('modernization_priority', 'HIGH')} |
| **Platform** | {detect_platform(parsed)} |
| **Project Type** | {project_type} |
| **Primary Language** | {primary.capitalize()} |
| **Tech Stack** | {tech_stack_str} |

**Priority Reasoning:** {summary.get('priority_reasoning', '')}

---

### 1.2 Codebase Metrics

| Language | Files | Share |
|----------|-------|-------|
{lang_rows}

| Metric | Value |
|--------|-------|
| Total Source Files | **{report['total_files']}** |
| Classes Defined | **{report['total_classes']}** |
| Methods & Functions | **{report['total_methods']}** |
| API Endpoints Extracted | **{len(endpoints)}** |
| Database Entities | **{db_s.get('entity_count', 0)}** |
| External Dependencies | **{ext_dep_count}** |
| Unreferenced Files | **{len(dead_code.get('dead_files', []))}** |

---

### 1.3 Architecture Layers

{arch_layers_md}

### System Block Diagram

![System Architecture Block Diagram]({repo_name}_block_diagram.svg)

<details>
<summary><b>Show ASCII Block Diagram (Offline / Plain-Text View)</b></summary>

```text
{ascii_diagram}
```
</details>

### Module Dependency Graph

![Module Dependency Graph]({repo_name}_dependency_graph.svg)

---

### 1.4 API Surface

**Total Endpoints:** {len(endpoints)}

{api_table}

---

### 1.5 Data Architecture

**Schema Summary**

| Metric | Value |
|--------|-------|
| Entities Detected | **{db_s.get('entity_count', 0)}** |
| Relationships | **{db_s.get('relationship_count', 0)}** |
| Bounded Contexts | **{len(data_boundaries or [])}** |

{db_entities_md}

**Proposed Microservice Boundaries (Database-Per-Service)**
{boundaries_md}

---

### 1.6 Top Connected Modules

| Module | Outgoing References |
|--------|-------------------|
{top_deps_md}

---

### 1.7 Modernization Roadmap

**Target Stack:** {target_stack_str}

{phases_md}

**Proposed Microservices:** {microservices_md}

**Risk Factors:**
{risk_factors_md}

**Estimated Effort:** {modernization.get('estimated_total_effort', 'N/A')}

---

### 1.8 Tech Debt Highlights

{concerns_md}

| Area | Severity | Details |
|------|----------|---------|
| Legacy Dependencies | HIGH | {ext_dep_count} external deps — audit for CVEs |
| Dead Code | {'MEDIUM' if len(dead_code.get('dead_files', [])) > 5 else 'LOW'} | {len(dead_code.get('dead_files', []))} unreferenced files |
| API Coverage | {'HIGH' if not endpoints else 'LOW'} | {len(endpoints)} endpoints documented |

---

## 2. Authentication & Access Control

> Detected authorization models: **{auth_type}**

### 2.1 Auth Summary

| Attribute | Value |
|-----------|-------|
| **Dominant Auth Model** | {auth_type} |
| **Auth Frameworks** | {', '.join(auth.get('auth_frameworks', [])) or 'None detected'} |
| **Named Roles** | {roles_md} |
| **Named Policies** | {policies_md} |
| **Protected Routes** | {len(auth.get('protected_routes', []))} |
| **Unguarded Routes** | {len(auth.get('public_routes', []))} |

### 2.2 Detected Auth Frameworks

{auth_frameworks_md}

---

### 2.3 RBAC — Role-Based Access Control

> Grants permissions based on named **roles** assigned to users.
> Example: `[Authorize(Roles="Admin")]`, `@PreAuthorize("hasRole('MANAGER')")`.

{rbac_table}

---

### 2.4 ABAC — Attribute/Policy-Based Access Control

> Grants permissions based on **attributes** (claims, policies, context).
> Example: `[Authorize(Policy="CanEditOrder")]`, `IAuthorizationRequirement`.

{abac_table}

---

### 2.5 ReBAC — Relationship-Based Access Control

> Grants permissions based on **relationships** between users and resources.
> Example: `IsOwner()`, `CreatedBy == currentUser`, Zanzibar-style tuples.

{rebac_table}

---

### 2.6 Route Protection Map

**Protected Routes (auth guard present):**

{protected_routes_md}

**Public / Unguarded Routes:**

{public_routes_md}

> ⚠️ Unguarded routes should be reviewed — some may be intentionally public
> (health checks, login endpoint) while others may require access control.

---

## 3. Business Logic Extractor

> Domain workflows, business rules, and entity glossary extracted from
> API endpoints, class names, and ORM entity model.

### 3.1 Business Domain

**Domain:** {bl_domain}

### What the System Does

{bl_what}

---

### 3.2 Core Business Workflows (End-to-End)

{bl_workflows_md}

---

### 3.3 User Roles & Actors

{bl_roles_md}

---

### 3.4 Key Business Rules

{bl_rules_md}

---

### 3.5 Domain Entity Glossary

{bl_entities_md}

---

### 3.6 External Integrations

{bl_integrations_md}

---

### 3.7 Codebase → Report Mapping

| Report Section | Key Files in Codebase |
|----------------|-----------------------|
| API / Endpoints | {', '.join(f'`{Path(ep["file"]).name}`' for ep in endpoints[:5]) or '_N/A_'} |
| Business Logic | {', '.join(f'`{Path(r["file"]).name}`' for r in parsed[:5] if any(k in r.get("file","").lower() for k in ("service","manager","business"))) or '_Inferred from services_'} |
| Data Entities | {', '.join(f'`{e.get("name","")}`' for e in db_s.get("entities",[])[:8]) or '_N/A_'} |

---

## 4. Screen-by-Screen Navigation

> End-to-end user journey through `{repo_name}` — every screen/page detected,
> what it does, and how users move between them.

**Project Type:** {project_type}
**Screens Detected:** {nav.get('screen_count', 0)}

---

### 4.1 Navigation Flow Diagram

{mermaid_nav}

---

### 4.2 Navigation Flow (Text)

{nav_flow_md}

---

### 4.3 Screen Inventory (Screen-by-Screen)

{screens_md}

---

### 4.4 End-to-End User Journey

Based on detected routes and screen names, a typical user journey through this
**{project_type}** application follows this path:

"""

    # Build narrative journey from nav flow
    visited = set()
    journey_steps = []
    # Start from login/home if available
    start_screens = [s["name"] for s in screens if any(k in s["name"].lower() for k in ("login", "home", "index", "default", "landing"))]
    start = start_screens[0] if start_screens else (screens[0]["name"] if screens else None)

    if start and nav_flow:
        queue = [start]
        while queue and len(journey_steps) < 12:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            # Find screen info
            screen_info = next((s for s in screens if s["name"] == current), None)
            desc = screen_info["description"] if screen_info else current
            journey_steps.append(f"**{current}** — {desc}")
            # Find outgoing edges
            outgoing = [e for e in nav_flow if e["from"] == current and e["to"] not in visited]
            for edge in outgoing[:2]:
                queue.append(edge["to"])

        for i, step in enumerate(journey_steps, 1):
            report_md += f"{i}. {step}\n"
    else:
        report_md += "_Detailed journey requires screen detection. Run against a project with view files (.aspx, .cshtml, .jsx, .vue, .html) for full navigation analysis._\n"

    report_md += f"""
---

## Appendix

### How This Report Was Generated

This report was produced by the **Reverse Engineer Skill** using pure static analysis:

1. Cloned the repository (`git clone --depth=1`)
2. Walked all source files (`.py`, `.java`, `.cs`, `.ts`, `.js`, `.aspx`, etc.)
3. Applied regex-based extraction for classes, methods, imports, and API routes
4. Detected authentication patterns (RBAC/ABAC/ReBAC) via code annotations
5. Identified screens and navigation flow from file paths and routing structures
6. Applied heuristics for business domain, workflows, and modernization roadmap

> **To get AI-powered narrative:** Open this report in Claude Code or GitHub Copilot
> and ask it to enhance any section with AI-quality analysis.

### Limitations

- Static analysis only — no runtime behaviour captured
- Auth detection based on patterns; dynamic or custom auth frameworks may not be detected
- Screen navigation is inferred from naming — actual route configuration may differ
- Business rules inferred from naming conventions — always validate with domain experts

---

_Generated by Reverse Engineer Skill · {now}_
"""

    return report_md
