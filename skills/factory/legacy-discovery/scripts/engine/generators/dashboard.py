"""
HTML Dashboard Generator
========================
Produces a professional, sidebar-based stakeholder dashboard as a
self-contained HTML file.

The dashboard includes six sections navigated via a fixed left sidebar:

1. **Overview** — key metric cards (count-up animation), horizontal bar chart
   for language distribution, system summary, tech stack badges, most-connected
   modules chart, and business logic domain card.
2. **Architecture** — vis.js interactive dependency network graph and
   architectural layer list.
3. **API Endpoints** — searchable endpoint table with HTTP method colour
   badges and a live count display.
4. **Dead Code** — SVG percentage ring showing the proportion of dead files,
   plus lists of unreferenced files and classes.
5. **How It Works** — Mermaid ``flowchart TB`` block diagram of the analysed
   system's architectural layers, plus full business logic explanation
   (domain, workflows, user roles, business rules, entity glossary).
6. **Data Architecture** — entity relationship network, schema metrics, and
   microservice data boundary decomposition.

Design principles:
- CSS variables only — no hardcoded colours in HTML or JS.
- Sidebar collapses to a hamburger menu on narrow screens.
- Dependency graph renders as a static SVG (hierarchical column layout).
- Block diagram renders with Mermaid.js (CDN, no server required).
- All navigation icons are inline SVGs (no external icon font).
- No emojis in navigation labels.
"""

import json
import datetime
from pathlib import Path


def generate_html_dashboard(
    repo_name,
    repo_url,
    report,
    endpoints,
    dead_code,
    tech_stack,
    summary,
    modernization,
    top_mods,
    platform="Cross-platform",
    arch_layers=None,
    db_schema=None,
    data_boundaries=None,
    business_logic=None,
    block_diagram=None,
    dep_graph=None,
):
    """Generate a professional sidebar-based stakeholder HTML dashboard.

    All analysis data is embedded in a ``DATA`` JavaScript object within the
    returned HTML string so the file is fully self-contained and requires no
    server.

    Args:
        repo_name (str): Repository name shown in the sidebar header and page
            title.
        repo_url (str): Original GitHub URL used for the repository link.
        report (dict): Metrics dict from
            :func:`engine.analyzer.generate_report` containing ``"languages"``,
            ``"total_files"``, ``"total_classes"``, and ``"total_methods"``.
        endpoints (list[dict]): API endpoint records from
            :func:`engine.analyzer.extract_api_endpoints` (up to 50 are
            displayed).
        dead_code (dict): Dead-code report with ``"dead_files"`` and
            ``"dead_classes"`` keys.
        mermaid_code (str): Mermaid ``graph TD`` diagram string.
        tech_stack (list[str]): Detected technology labels.
        summary (dict): AI executive summary dict with ``"purpose"``,
            ``"architecture_pattern"``, ``"tech_debt_concerns"``,
            ``"modernization_priority"``, and ``"priority_reasoning"`` keys.
        modernization (dict): AI modernisation roadmap dict with ``"phases"``,
            ``"target_stack"``, ``"microservices_boundaries"``,
            ``"estimated_total_effort"``, and ``"risk_factors"`` keys.
        top_mods (list[tuple[str, int]]): Most-connected modules list from
            :func:`engine.analyzer.find_top_modules` (up to 8 shown).
        platform (str): Runtime platform label.  Defaults to
            ``"Cross-platform"``.
        arch_layers (list[str] | None): Detected architecture layer labels.
            When ``None`` (default) an empty list is used.
        db_schema (dict | None): Database schema dict from
            :func:`engine.analyzer.detect_database_schema`.  When ``None``
            an empty schema is used.
        data_boundaries (list[dict] | None): Microservice data boundary dicts
            from :func:`engine.analyzer.suggest_microservice_data_boundaries`.
            When ``None`` an empty list is used.

    Returns:
        str: A complete, self-contained HTML document as a string.
    """
    if arch_layers is None:
        arch_layers = []
    if db_schema is None:
        db_schema = {"entities": [], "entity_count": 0, "relationship_count": 0, "has_schema": False}
    if data_boundaries is None:
        data_boundaries = []
    if business_logic is None:
        business_logic = {
            "business_domain": "General Business Application",
            "what_it_does": "",
            "core_workflows": [],
            "user_roles": [],
            "key_business_rules": [],
            "data_entities_explained": [],
            "integrations": [],
            "fallback_used": True,
        }

    # ------------------------------------------------------------------
    # Prepare JavaScript-embeddable data
    # ------------------------------------------------------------------
    lang_dist_js     = json.dumps(report.get("languages", {}))
    top_mods_js      = json.dumps([{"module": m, "connections": c} for m, c in top_mods[:8]])
    endpoints_js     = json.dumps([
        {
            "path":    ep["path"],
            "methods": ep["methods"],
            "handler": f"{ep.get('class') or 'global'}.{ep.get('method') or 'handler'}()",
            "file":    Path(ep["file"]).name,
        }
        for ep in endpoints[:50]
    ])
    dead_files_js    = json.dumps([Path(f).name for f in dead_code.get("dead_files", [])[:20]])
    dead_classes_js  = json.dumps([
        {"class": d["class"], "file": Path(d["file"]).name}
        for d in dead_code.get("dead_classes", [])[:20]
    ])
    tech_stack_js    = json.dumps(tech_stack)
    arch_pattern_js  = json.dumps(summary.get("architecture_pattern", "Monolithic"))
    arch_layers_js   = json.dumps(arch_layers)
    phases_js        = json.dumps(modernization.get("phases", []))
    microservices_js = json.dumps(modernization.get("microservices_boundaries", []))
    target_stack_js  = json.dumps(modernization.get("target_stack", []))
    # Sanitise db_schema entities for JS: drop full file paths, keep only filename
    _db_entities_js = []
    for ent in db_schema.get("entities", []):
        _db_entities_js.append({
            "name":          ent.get("name", ""),
            "table":         ent.get("table", ""),
            "fields":        ent.get("fields", [])[:20],
            "relationships": ent.get("relationships", [])[:10],
            "file":          Path(ent.get("file", "")).name,
        })
    db_schema_js = json.dumps({
        "entity_count":       db_schema.get("entity_count", 0),
        "relationship_count": db_schema.get("relationship_count", 0),
        "has_schema":         db_schema.get("has_schema", False),
        "entities":           _db_entities_js,
    })
    data_boundaries_js  = json.dumps(data_boundaries)
    business_logic_js   = json.dumps({
        "business_domain":         business_logic.get("business_domain", ""),
        "what_it_does":            business_logic.get("what_it_does", ""),
        "core_workflows":          business_logic.get("core_workflows", []),
        "user_roles":              business_logic.get("user_roles", []),
        "key_business_rules":      business_logic.get("key_business_rules", []),
        "data_entities_explained": business_logic.get("data_entities_explained", []),
        "integrations":            business_logic.get("integrations", []),
        "fallback_used":           business_logic.get("fallback_used", True),
    })
    block_diagram_js    = json.dumps(block_diagram if isinstance(block_diagram, dict) else {})
    dep_graph_js        = json.dumps(dep_graph or {"nodes": [], "edges": []})
    priority         = summary.get("modernization_priority", "HIGH")
    generated_at     = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%B %d, %Y at %H:%M UTC"
    )

    # Dead-code percentage for the SVG ring
    total_files  = report.get("total_files", 1) or 1
    dead_count   = len(dead_code.get("dead_files", []))
    dead_pct     = round(dead_count / total_files * 100)
    # SVG circle: circumference = 2*pi*r  (r=40)
    circ         = 251.2
    dead_dash    = round(dead_pct / 100 * circ, 1)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{repo_name} — Reverse Engineering Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@hpcc-js/wasm@2.20.0/dist/index.min.js"></script>
<style>
/* ================================================================
   CSS Variables — single source of truth for all colours
   ================================================================ */
:root {{
  --sidebar-bg:        #1c1c1e;
  --sidebar-text:      rgba(235,235,245,0.8);
  --sidebar-text-dim:  rgba(235,235,245,0.4);
  --sidebar-active:    #0071e3;
  --sidebar-active-bg: rgba(0,113,227,0.15);
  --sidebar-width:     240px;

  --bg:       #f5f5f7;
  --surface:  #ffffff;
  --surface2: #f9f9fb;
  --border:   rgba(0,0,0,0.08);

  --blue:       #0071e3;
  --blue-light: rgba(0,113,227,0.08);
  --green:      #30d158;
  --orange:     #ff9f0a;
  --red:        #ff453a;
  --purple:     #bf5af2;

  --text:  #1d1d1f;
  --text2: #6e6e73;
  --text3: #aeaeb2;

  --shadow:    0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.06);
  --shadow-md: 0 4px 24px rgba(0,0,0,0.10);
  --radius:    14px;
  --radius-sm: 9px;
}}

/* ================================================================
   Reset & base
   ================================================================ */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ height: 100%; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  -webkit-font-smoothing: antialiased;
  display: flex;
}}

/* ================================================================
   Sidebar
   ================================================================ */
.sidebar {{
  width: var(--sidebar-width);
  min-height: 100vh;
  background: var(--sidebar-bg);
  display: flex;
  flex-direction: column;
  position: fixed;
  top: 0; left: 0; bottom: 0;
  z-index: 200;
  transition: transform 0.28s ease;
}}

.sidebar-header {{
  padding: 24px 20px 20px;
  border-bottom: 1px solid rgba(255,255,255,0.07);
}}
.sidebar-logo {{
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}}
.sidebar-logo-icon {{
  width: 36px; height: 36px;
  background: var(--blue);
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}}
.sidebar-logo-icon svg {{ color: #fff; }}
.sidebar-repo {{
  font-size: 15px;
  font-weight: 700;
  color: #fff;
  letter-spacing: -0.2px;
  line-height: 1.2;
  word-break: break-all;
}}
.sidebar-sub {{
  font-size: 11px;
  color: var(--sidebar-text-dim);
  margin-top: 6px;
  letter-spacing: 0.02em;
}}

.sidebar-nav {{
  flex: 1;
  padding: 16px 10px;
  overflow-y: auto;
}}

.nav-item {{
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  color: var(--sidebar-text);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  border: none;
  background: none;
  width: 100%;
  text-align: left;
  margin-bottom: 2px;
}}
.nav-item:hover {{
  background: rgba(255,255,255,0.06);
  color: #fff;
}}
.nav-item.active {{
  background: var(--sidebar-active-bg);
  color: var(--sidebar-active);
}}
.nav-item svg {{ flex-shrink: 0; opacity: 0.85; }}
.nav-item.active svg {{ opacity: 1; }}

.sidebar-footer {{
  padding: 16px 20px;
  border-top: 1px solid rgba(255,255,255,0.07);
  font-size: 11px;
  color: var(--sidebar-text-dim);
  line-height: 1.5;
}}

/* Hamburger (mobile) */
.hamburger {{
  display: none;
  position: fixed;
  top: 14px; left: 14px;
  z-index: 300;
  background: var(--sidebar-bg);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  padding: 8px;
  cursor: pointer;
  color: #fff;
}}
.sidebar-overlay {{
  display: none;
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.5);
  z-index: 150;
}}

/* ================================================================
   Main content
   ================================================================ */
.main-content {{
  margin-left: var(--sidebar-width);
  flex: 1;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}}

/* ================================================================
   Section header (sticky)
   ================================================================ */
.section-header {{
  background: rgba(245,245,247,0.92);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
  padding: 20px 40px;
  position: sticky; top: 0; z-index: 100;
}}
.section-title {{
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.4px;
  color: var(--text);
  border-left: 3px solid var(--blue);
  padding-left: 12px;
}}
.section-subtitle {{
  font-size: 13px;
  color: var(--text2);
  margin-top: 4px;
  padding-left: 15px;
}}

/* ================================================================
   Content area
   ================================================================ */
.content-area {{
  padding: 32px 40px;
  flex: 1;
}}

.tab-panel {{ display: none; }}
.tab-panel.active {{ display: block; }}

/* ================================================================
   Metric cards
   ================================================================ */
.metrics-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 28px;
}}
.metric-card {{
  background: var(--surface);
  border-radius: var(--radius);
  padding: 22px 20px;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  gap: 8px;
}}
.metric-icon-wrap {{
  width: 40px; height: 40px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 4px;
}}
.metric-label {{
  font-size: 11px;
  font-weight: 600;
  color: var(--text2);
  text-transform: uppercase;
  letter-spacing: 0.07em;
}}
.metric-value {{
  font-size: 34px;
  font-weight: 700;
  letter-spacing: -1px;
  color: var(--text);
  line-height: 1;
}}
.metric-sub {{
  font-size: 12px;
  color: var(--text3);
}}

/* ================================================================
   Cards
   ================================================================ */
.card {{
  background: var(--surface);
  border-radius: var(--radius);
  padding: 24px;
  box-shadow: var(--shadow);
}}
.card-title {{
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 18px;
  display: flex;
  align-items: center;
  gap: 8px;
}}
.card-title-icon {{
  width: 28px; height: 28px;
  border-radius: 7px;
  background: var(--blue-light);
  display: flex; align-items: center; justify-content: center;
  color: var(--blue);
}}

/* ================================================================
   Grid layouts
   ================================================================ */
.two-col {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}}
.three-col {{
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}}

/* ================================================================
   Horizontal bar chart (language distribution)
   ================================================================ */
.hbar-list {{ display: flex; flex-direction: column; gap: 12px; }}
.hbar-row {{ display: flex; align-items: center; gap: 12px; }}
.hbar-lang {{
  width: 88px;
  font-size: 13px;
  color: var(--text2);
  text-align: right;
  flex-shrink: 0;
}}
.hbar-track {{
  flex: 1;
  height: 8px;
  background: var(--bg);
  border-radius: 4px;
  overflow: hidden;
}}
.hbar-fill {{
  height: 100%;
  border-radius: 4px;
  transition: width 1s cubic-bezier(.4,0,.2,1);
}}
.hbar-count {{
  width: 32px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text);
  flex-shrink: 0;
}}

/* ================================================================
   Stat rows
   ================================================================ */
.stat-row {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
}}
.stat-row:last-child {{ border-bottom: none; }}
.stat-label {{ color: var(--text2); }}
.stat-val {{ font-weight: 600; color: var(--text); }}

/* ================================================================
   Tech badges
   ================================================================ */
.badge-wrap {{ display: flex; flex-wrap: wrap; gap: 8px; }}
.badge {{
  padding: 5px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  background: var(--bg);
  color: var(--text2);
  border: 1px solid var(--border);
}}
.badge.blue {{
  background: var(--blue-light);
  color: var(--blue);
  border-color: transparent;
}}
.badge.green {{
  background: rgba(48,209,88,0.1);
  color: var(--green);
  border-color: transparent;
}}

/* ================================================================
   Priority badge
   ================================================================ */
.priority-pill {{
  display: inline-flex;
  align-items: center;
  padding: 5px 14px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
}}

/* ================================================================
   Module bars
   ================================================================ */
.mod-bars {{ display: flex; flex-direction: column; gap: 10px; }}
.mod-row {{ display: flex; flex-direction: column; gap: 4px; }}
.mod-label {{
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text2);
}}
.mod-track {{
  height: 6px;
  background: var(--bg);
  border-radius: 3px;
  overflow: hidden;
}}
.mod-fill {{
  height: 100%;
  border-radius: 3px;
  background: linear-gradient(90deg, var(--blue), #5ac8fa);
}}


/* ================================================================
   Architecture layers
   ================================================================ */
.layer-chip {{
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 14px;
  border-radius: var(--radius-sm);
  background: var(--bg);
  border: 1px solid var(--border);
  font-size: 13px;
  color: var(--text2);
  margin: 4px;
}}

/* ================================================================
   API search + table
   ================================================================ */
.search-bar {{
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}}
.search-input {{
  flex: 1;
  padding: 9px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--text);
  background: var(--bg);
  outline: none;
  transition: border-color 0.15s;
}}
.search-input:focus {{ border-color: var(--blue); background: #fff; }}
.search-count {{
  font-size: 12px;
  color: var(--text2);
  white-space: nowrap;
}}

.data-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
.data-table th {{
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: var(--text2);
  text-transform: uppercase;
  letter-spacing: 0.07em;
  padding: 9px 12px;
  border-bottom: 1px solid var(--border);
}}
.data-table td {{
  padding: 11px 12px;
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}}
.data-table tr:last-child td {{ border-bottom: none; }}
.data-table tbody tr:hover td {{ background: var(--surface2); }}

.method-pill {{
  display: inline-block;
  padding: 2px 8px;
  border-radius: 5px;
  font-size: 11px;
  font-weight: 700;
  font-family: "SF Mono", "Fira Code", monospace;
  margin-right: 3px;
}}
.GET    {{ background: rgba(48,209,88,0.12);  color: #1a8c3a; }}
.POST   {{ background: rgba(0,113,227,0.10);  color: var(--blue); }}
.PUT    {{ background: rgba(255,159,10,0.12); color: #a05800; }}
.DELETE {{ background: rgba(255,69,58,0.10);  color: #c0392b; }}
.PATCH  {{ background: rgba(191,90,242,0.10); color: #8a35b5; }}

.code-mono {{
  font-family: "SF Mono", "Fira Code", monospace;
  font-size: 12px;
  color: var(--text2);
  background: var(--bg);
  padding: 2px 6px;
  border-radius: 4px;
}}

/* ================================================================
   Dead code — SVG ring
   ================================================================ */
.dead-ring-wrap {{
  display: flex;
  align-items: center;
  gap: 28px;
  margin-bottom: 20px;
}}
.dead-ring-label {{
  text-align: center;
}}
.dead-ring-pct {{
  font-size: 28px;
  font-weight: 700;
  color: var(--text);
}}
.dead-ring-sub {{
  font-size: 12px;
  color: var(--text2);
  margin-top: 2px;
}}

.dead-list {{ list-style: none; padding: 0; display: flex; flex-direction: column; gap: 8px; }}
.dead-item {{
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 12px;
  font-family: "SF Mono", "Fira Code", monospace;
  color: var(--text2);
  padding: 7px 10px;
  background: var(--surface2);
  border-radius: var(--radius-sm);
}}
.dead-dot {{
  width: 7px; height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}}

/* ================================================================
   How It Works — block diagram + business logic
   ================================================================ */
.timeline {{
  position: relative;
  padding-left: 32px;
}}
.timeline::before {{
  content: "";
  position: absolute;
  left: 11px; top: 0; bottom: 0;
  width: 2px;
  background: var(--border);
  border-radius: 1px;
}}

.timeline-item {{
  position: relative;
  margin-bottom: 32px;
}}
.timeline-item:last-child {{ margin-bottom: 0; }}

.timeline-dot {{
  position: absolute;
  left: -28px; top: 4px;
  width: 16px; height: 16px;
  border-radius: 50%;
  border: 2px solid var(--surface);
  z-index: 1;
}}

.timeline-content {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 18px 20px;
  box-shadow: var(--shadow);
}}
.timeline-header {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}}
.timeline-phase {{
  font-size: 11px;
  font-weight: 600;
  color: var(--text3);
  text-transform: uppercase;
  letter-spacing: 0.07em;
}}
.timeline-risk {{
  font-size: 11px;
  font-weight: 700;
  padding: 2px 10px;
  border-radius: 20px;
}}
.timeline-title {{
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 4px;
}}
.timeline-duration {{
  font-size: 12px;
  color: var(--text2);
  margin-bottom: 12px;
}}
.timeline-tasks {{
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}}
.timeline-tasks li {{
  font-size: 13px;
  color: var(--text2);
  padding-left: 18px;
  position: relative;
}}
.timeline-tasks li::before {{
  content: "";
  position: absolute;
  left: 0; top: 6px;
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--blue);
  opacity: 0.6;
}}

/* ================================================================
   Microservice grid
   ================================================================ */
.micro-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px,1fr));
  gap: 12px;
  margin-top: 12px;
}}
.micro-card {{
  background: var(--blue-light);
  border-radius: var(--radius-sm);
  padding: 16px;
  text-align: center;
  font-size: 13px;
  font-weight: 500;
  color: var(--blue);
  border: 1px solid rgba(0,113,227,0.15);
}}
.micro-card-icon {{
  width: 32px; height: 32px;
  margin: 0 auto 8px;
  background: var(--blue);
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
}}
.micro-card-icon svg {{ color: #fff; }}

/* ================================================================
   Concerns list
   ================================================================ */
.concern-list {{ display: flex; flex-direction: column; gap: 10px; }}
.concern-item {{
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 13px;
  color: var(--text);
  padding: 10px 12px;
  background: rgba(255,159,10,0.06);
  border-left: 3px solid var(--orange);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}}
.concern-icon {{
  color: var(--orange);
  flex-shrink: 0;
  margin-top: 1px;
}}

/* ================================================================
   Data Architecture — boundary cards and entity table
   ================================================================ */
.boundary-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
}}
.boundary-card {{
  border-radius: var(--radius-sm);
  padding: 16px;
  border: 1px solid var(--border);
  background: var(--surface2);
}}
.boundary-card-header {{
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}}
.boundary-dot {{
  width: 10px; height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}}
.boundary-name {{
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  flex: 1;
}}
.boundary-count {{
  font-size: 11px;
  color: var(--text3);
  font-weight: 500;
}}
.entity-chips {{
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}}
.entity-chip {{
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 4px;
  font-family: "SF Mono", "Fira Code", monospace;
  border: 1px solid var(--border);
  color: var(--text2);
  background: var(--bg);
}}

/* ================================================================
   Responsive — sidebar collapse
   ================================================================ */
@media (max-width: 860px) {{
  .sidebar {{
    transform: translateX(calc(-1 * var(--sidebar-width)));
  }}
  .sidebar.open {{
    transform: translateX(0);
  }}
  .sidebar-overlay.open {{ display: block; }}
  .hamburger {{ display: flex; }}
  .main-content {{ margin-left: 0; }}
  .two-col, .three-col {{ grid-template-columns: 1fr; }}
  .section-header {{ padding: 16px 20px; }}
  .content-area {{ padding: 20px; }}
}}
</style>
</head>
<body>

<!-- Hamburger button (mobile only) -->
<button class="hamburger" onclick="toggleSidebar()" aria-label="Toggle menu">
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <line x1="3" y1="6"  x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/>
    <line x1="3" y1="18" x2="21" y2="18"/>
  </svg>
</button>
<div class="sidebar-overlay" id="sidebar-overlay" onclick="toggleSidebar()"></div>

<!-- ================================================================
     SIDEBAR
     ================================================================ -->
<aside class="sidebar" id="sidebar">
  <div class="sidebar-header">
    <div class="sidebar-logo">
      <div class="sidebar-logo-icon">
        <!-- Code icon -->
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
        </svg>
      </div>
      <div class="sidebar-repo">{repo_name}</div>
    </div>
    <div class="sidebar-sub">Reverse Engineering Dashboard</div>
  </div>

  <nav class="sidebar-nav">
    <!-- Overview -->
    <button class="nav-item active" onclick="switchSection('overview', this)">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
        <rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
      </svg>
      Overview
    </button>
    <!-- Architecture -->
    <button class="nav-item" onclick="switchSection('architecture', this)">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="5" r="3"/><circle cx="5" cy="19" r="3"/><circle cx="19" cy="19" r="3"/>
        <line x1="12" y1="8" x2="5" y2="16"/><line x1="12" y1="8" x2="19" y2="16"/>
      </svg>
      Architecture
    </button>
    <!-- API Endpoints -->
    <button class="nav-item" onclick="switchSection('api', this)">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
      </svg>
      API Endpoints
    </button>
    <!-- Dead Code -->
    <button class="nav-item" onclick="switchSection('deadcode', this)">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
      </svg>
      Dead Code
    </button>
    <!-- How It Works -->
    <button class="nav-item" onclick="switchSection('howitworks', this)">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="3" width="7" height="7" rx="1"/>
        <rect x="14" y="3" width="7" height="7" rx="1"/>
        <rect x="3" y="14" width="7" height="7" rx="1"/>
        <rect x="14" y="14" width="7" height="7" rx="1"/>
        <line x1="10" y1="6.5" x2="14" y2="6.5"/>
        <line x1="6.5" y1="10" x2="6.5" y2="14"/>
        <line x1="17.5" y1="10" x2="17.5" y2="14"/>
        <line x1="10" y1="17.5" x2="14" y2="17.5"/>
      </svg>
      How It Works
    </button>
    <!-- Data Architecture -->
    <button class="nav-item" onclick="switchSection('dataarch', this)">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <ellipse cx="12" cy="5" rx="9" ry="3"/>
        <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
        <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
      </svg>
      Data Architecture
    </button>
  </nav>

  <div class="sidebar-footer">
    Generated by Reverse Engineer Skill<br>
    Powered by claude-sonnet-4-6<br>
    <span style="color:rgba(235,235,245,0.25)">{generated_at}</span>
  </div>
</aside>

<!-- ================================================================
     MAIN CONTENT
     ================================================================ -->
<div class="main-content">

  <!-- ============================================================
       SECTION: OVERVIEW
       ============================================================ -->
  <div id="section-overview" class="tab-panel active">
    <div class="section-header">
      <div class="section-title">Project Overview</div>
      <div class="section-subtitle">Complete reverse engineering analysis of {repo_name}</div>
    </div>
    <div class="content-area">

      <!-- Metric cards -->
      <div class="metrics-grid" id="metrics-grid"></div>

      <!-- Language chart + System summary -->
      <div class="two-col" style="margin-bottom:20px">
        <div class="card">
          <div class="card-title">
            <div class="card-title-icon">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/>
                <line x1="6" y1="20" x2="6" y2="14"/>
              </svg>
            </div>
            Language Distribution
          </div>
          <div class="hbar-list" id="lang-hbar"></div>
        </div>

        <div class="card">
          <div class="card-title">
            <div class="card-title-icon">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>
              </svg>
            </div>
            System Summary
          </div>
          <p id="purpose-text" style="font-size:13px;color:var(--text2);line-height:1.65;margin-bottom:16px"></p>
          <div class="stat-row">
            <span class="stat-label">Architecture Pattern</span>
            <span class="stat-val" id="arch-pattern-text"></span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Modernization Priority</span>
            <span id="priority-badge"></span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Est. Modernization Effort</span>
            <span class="stat-val" id="effort-text"></span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Platform</span>
            <span class="stat-val">{platform}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Repository</span>
            <a href="{repo_url}" target="_blank" rel="noopener"
               style="font-size:12px;color:var(--blue);text-decoration:none;word-break:break-all"
               onmouseover="this.style.textDecoration='underline'"
               onmouseout="this.style.textDecoration='none'">{repo_url}</a>
          </div>
        </div>
      </div>

      <!-- Tech stack + Most connected modules -->
      <div class="two-col">
        <div class="card">
          <div class="card-title">
            <div class="card-title-icon">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="16 3 21 3 21 8"/><line x1="4" y1="20" x2="21" y2="3"/>
                <polyline points="21 16 21 21 16 21"/><line x1="15" y1="15" x2="21" y2="21"/>
              </svg>
            </div>
            Detected Tech Stack
          </div>
          <div class="badge-wrap" id="tech-stack-wrap"></div>
        </div>

        <div class="card">
          <div class="card-title">
            <div class="card-title-icon">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/>
                <circle cx="18" cy="19" r="3"/>
                <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/>
                <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
              </svg>
            </div>
            Most Connected Modules
          </div>
          <div class="mod-bars" id="modules-bars"></div>
        </div>
      </div>

      <!-- Business Logic overview card -->
      <div class="card" style="margin-top:20px" id="bl-card">
        <div class="card-title">
          <div class="card-title-icon">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
            </svg>
          </div>
          Business Logic &amp; Domain
        </div>
        <div id="bl-domain-badge" style="margin-bottom:14px"></div>
        <p id="bl-what" style="font-size:13px;color:var(--text2);line-height:1.65;margin-bottom:18px"></p>
        <div class="two-col" style="gap:16px;margin-bottom:0">
          <div>
            <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--text2);margin-bottom:10px">User Roles</div>
            <div class="badge-wrap" id="bl-roles"></div>
          </div>
          <div>
            <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--text2);margin-bottom:10px">Integrations</div>
            <div class="badge-wrap" id="bl-integrations"></div>
          </div>
        </div>
        <div style="margin-top:18px">
          <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--text2);margin-bottom:10px">Key Business Rules</div>
          <ul id="bl-rules" style="font-size:13px;color:var(--text2);padding-left:18px;line-height:1.8"></ul>
        </div>
      </div>

    </div>
  </div>

  <!-- ============================================================
       SECTION: ARCHITECTURE
       ============================================================ -->
  <div id="section-architecture" class="tab-panel">
    <div class="section-header">
      <div class="section-title">Architecture &amp; Dependencies</div>
      <div class="section-subtitle">Dependency graph and inferred architectural layers</div>
    </div>
    <div class="content-area">

      <div class="card" style="margin-bottom:20px">
        <div class="card-title">
          <div class="card-title-icon">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="5" r="3"/><circle cx="5" cy="19" r="3"/><circle cx="19" cy="19" r="3"/>
              <line x1="12" y1="8" x2="5" y2="16"/><line x1="12" y1="8" x2="19" y2="16"/>
            </svg>
          </div>
          Dependency Graph
        </div>
        <div style="width:100%; border:1px solid var(--border); border-radius:8px; background:var(--surface1); padding:16px; box-sizing:border-box;">
          <img src="{repo_name}_dependency_graph.svg" alt="Module Dependency Graph" style="width:100%; max-height:550px; object-fit:contain; display:block; margin:0 auto; border-radius:6px;" />
        </div>
      </div>

      <div class="two-col">
        <div class="card">
          <div class="card-title">
            <div class="card-title-icon">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="4" rx="1"/><rect x="3" y="10" width="18" height="4" rx="1"/>
                <rect x="3" y="17" width="18" height="4" rx="1"/>
              </svg>
            </div>
            Architectural Layers
          </div>
          <div id="layers-list" style="display:flex;flex-wrap:wrap;margin:-4px"></div>
        </div>

        <div class="card">
          <div class="card-title">
            <div class="card-title-icon">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/>
                <line x1="6" y1="20" x2="6" y2="14"/>
              </svg>
            </div>
            Dependency Stats
          </div>
          <div id="dep-stats"></div>
        </div>
      </div>

    </div>
  </div>

  <!-- ============================================================
       SECTION: API ENDPOINTS
       ============================================================ -->
  <div id="section-api" class="tab-panel">
    <div class="section-header">
      <div class="section-title">API Endpoints</div>
      <div class="section-subtitle">Auto-extracted from routing annotations and decorators</div>
    </div>
    <div class="content-area">
      <div class="card">
        <div class="card-title">
          <div class="card-title-icon">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
            </svg>
          </div>
          Endpoint Catalog
        </div>
        <div class="search-bar">
          <input type="text" class="search-input" id="api-search"
                 placeholder="Search endpoints, paths, handlers..."
                 oninput="filterEndpoints(this.value)">
          <span class="search-count" id="ep-count"></span>
        </div>
        <div id="endpoints-table-wrap"></div>
      </div>
    </div>
  </div>

  <!-- ============================================================
       SECTION: DEAD CODE
       ============================================================ -->
  <div id="section-deadcode" class="tab-panel">
    <div class="section-header">
      <div class="section-title">Dead Code Analysis</div>
      <div class="section-subtitle">Unreferenced files and classes detected by static analysis</div>
    </div>
    <div class="content-area">

      <!-- Ring summary -->
      <div class="card" style="margin-bottom:20px">
        <div class="dead-ring-wrap">
          <svg width="100" height="100" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="40"
              fill="none" stroke="var(--bg)" stroke-width="10"/>
            <circle cx="50" cy="50" r="40"
              fill="none" stroke="var(--orange)" stroke-width="10"
              stroke-dasharray="{dead_dash} {circ}"
              stroke-dashoffset="62.8"
              stroke-linecap="round"
              transform="rotate(-90 50 50)"/>
          </svg>
          <div>
            <div class="dead-ring-pct">{dead_pct}%</div>
            <div class="dead-ring-sub">of analyzed files flagged as dead</div>
            <div style="margin-top:10px;font-size:13px;color:var(--text2)">
              <strong style="color:var(--text)">{dead_count}</strong> of
              <strong style="color:var(--text)">{total_files}</strong> files potentially unreferenced
            </div>
          </div>
          <div style="flex:1;font-size:12px;color:var(--text2);line-height:1.6;max-width:340px">
            Dead code detection is heuristic — a file is flagged when its stem does not appear in any
            other file's imports and none of its classes are referenced. Always review manually before
            removing.
          </div>
        </div>
      </div>

      <div class="two-col">
        <div class="card">
          <div class="card-title">
            <div class="card-title-icon">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
            </div>
            Unreferenced Files
          </div>
          <ul class="dead-list" id="dead-files-list"></ul>
        </div>
        <div class="card">
          <div class="card-title">
            <div class="card-title-icon">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
              </svg>
            </div>
            Unreferenced Classes
          </div>
          <ul class="dead-list" id="dead-classes-list"></ul>
        </div>
      </div>

    </div>
  </div>

  <!-- ============================================================
       SECTION: HOW IT WORKS
       ============================================================ -->
  <div id="section-howitworks" class="tab-panel">
    <div class="section-header">
      <div class="section-title">How It Works</div>
      <div class="section-subtitle">Architectural block diagram and complete business logic explanation</div>
    </div>
    <div class="content-area">

      <!-- Block Diagram -->
      <div class="card" style="margin-bottom:24px">
        <div class="card-title">
          <div class="card-title-icon">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="7" height="7" rx="1"/>
              <rect x="14" y="3" width="7" height="7" rx="1"/>
              <rect x="3" y="14" width="7" height="7" rx="1"/>
              <rect x="14" y="14" width="7" height="7" rx="1"/>
            </svg>
          </div>
          System Architecture Block Diagram
        </div>
        <div id="block-diagram-container" style="background:var(--surface2);border-radius:8px;padding:20px;overflow:auto;min-height:200px;display:flex;align-items:center;justify-content:center">
          <div id="block-diagram-graphviz" style="width:100%;display:flex;justify-content:center"></div>
        </div>
        <p id="block-diagram-fallback" style="display:none;font-size:13px;color:var(--text2);padding:12px;font-family:monospace;white-space:pre-wrap;background:var(--surface2);border-radius:8px;margin-top:8px"></p>
      </div>

      <!-- Business Logic Full Explanation -->
      <div class="card" style="margin-bottom:24px">
        <div class="card-title">
          <div class="card-title-icon">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
          </div>
          What This System Does
        </div>
        <div style="margin-bottom:12px">
          <span class="badge blue" id="hiw-domain-badge" style="font-size:13px;padding:5px 12px"></span>
        </div>
        <div id="hiw-what" style="font-size:14px;line-height:1.7;color:var(--text)"></div>
      </div>

      <!-- Core Workflows -->
      <div class="card" style="margin-bottom:24px">
        <div class="card-title">
          <div class="card-title-icon">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
            </svg>
          </div>
          Core Business Workflows
        </div>
        <div id="hiw-workflows"></div>
      </div>

      <!-- Roles + Rules row -->
      <div class="two-col" style="margin-bottom:24px">
        <div class="card">
          <div class="card-title">
            <div class="card-title-icon">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                <circle cx="9" cy="7" r="4"/>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
              </svg>
            </div>
            User Roles &amp; Actors
          </div>
          <div class="badge-wrap" id="hiw-roles" style="margin-top:8px"></div>
        </div>

        <div class="card">
          <div class="card-title">
            <div class="card-title-icon">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 3H5a2 2 0 0 0-2 2v4m6-6h10a2 2 0 0 1 2 2v4M9 3v18m0 0h10a2 2 0 0 0 2-2V9M9 21H5a2 2 0 0 1-2-2V9m0 0h18"/>
              </svg>
            </div>
            Key Business Rules
          </div>
          <ul id="hiw-rules" style="margin:8px 0 0 0;padding-left:18px;font-size:13px;color:var(--text);line-height:1.7"></ul>
        </div>
      </div>

      <!-- Entity Glossary -->
      <div class="card" style="margin-bottom:24px">
        <div class="card-title">
          <div class="card-title-icon">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
            </svg>
          </div>
          Domain Entity Glossary
        </div>
        <div id="hiw-entities" style="margin-top:8px"></div>
      </div>

      <!-- Integrations -->
      <div class="card">
        <div class="card-title">
          <div class="card-title-icon">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
            </svg>
          </div>
          Detected External Integrations
        </div>
        <div class="badge-wrap" id="hiw-integrations" style="margin-top:8px"></div>
      </div>

    </div>
  </div>

  <!-- ============================================================
       SECTION: DATA ARCHITECTURE
       ============================================================ -->
  <div id="section-dataarch" class="tab-panel">
    <div class="section-header">
      <div class="section-title">Data Architecture</div>
      <div class="section-subtitle">Database schema, entity relationships, and microservice data decomposition</div>
    </div>
    <div class="content-area">

      <!-- Metric mini-cards -->
      <div class="metrics-grid" style="grid-template-columns:repeat(auto-fit,minmax(180px,1fr));margin-bottom:24px" id="db-metrics"></div>

      <!-- Entity Relationship Diagram -->
      <div class="card" style="margin-bottom:20px">
        <div class="card-title">
          <div class="card-title-icon">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <ellipse cx="12" cy="5" rx="9" ry="3"/>
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
            </svg>
          </div>
          Entity Relationship Diagram
        </div>
        <div class="network-wrap" style="height:420px" id="entity-net-wrap">
          <div id="entity-network" style="width:100%;height:100%"></div>
          <div class="network-legend" id="entity-legend"></div>
        </div>
        <p style="font-size:11px;color:var(--text3);margin-top:8px">
          Nodes are coloured by proposed microservice boundary. Drag to explore &middot; Scroll to zoom.
        </p>
      </div>

      <!-- Bounded Contexts -->
      <div class="card" style="margin-bottom:20px">
        <div class="card-title">
          <div class="card-title-icon">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="7" width="6" height="10" rx="1"/>
              <rect x="9" y="3" width="6" height="14" rx="1"/>
              <rect x="16" y="7" width="6" height="10" rx="1"/>
            </svg>
          </div>
          Proposed Microservice Data Boundaries
        </div>
        <p style="font-size:12px;color:var(--text2);margin-bottom:14px;line-height:1.6">
          Entities grouped by semantic domain &mdash; each group represents a candidate microservice
          owning its own database. <strong style="color:var(--text)">Database-per-service</strong>
          is the recommended pattern when migrating from a shared monolithic schema.
        </p>
        <div class="boundary-grid" id="boundary-grid"></div>
      </div>

      <!-- Entity Table -->
      <div class="card">
        <div class="card-title">
          <div class="card-title-icon">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
          </div>
          Detected Entities
        </div>
        <div id="entity-table-wrap"></div>
      </div>

    </div>
  </div>

</div><!-- end .main-content -->

<!-- ================================================================
     DATA + SCRIPTS
     ================================================================ -->
<script>
const DATA = {{
  repoName:    {json.dumps(repo_name)},
  repoUrl:     {json.dumps(repo_url)},
  metrics: {{
    files:     {report['total_files']},
    classes:   {report['total_classes']},
    methods:   {report['total_methods']},
    endpoints: {len(endpoints)},
    deadFiles: {dead_count},
  }},
  languages:   {lang_dist_js},
  topModules:  {top_mods_js},
  endpoints:   {endpoints_js},
  deadFiles:   {dead_files_js},
  deadClasses: {dead_classes_js},
  techStack:   {tech_stack_js},
  archPattern: {arch_pattern_js},
  priority:    {json.dumps(priority)},
  purpose:     {json.dumps(summary.get('purpose', ''))},
  effort:      {json.dumps(modernization.get('estimated_total_effort', 'N/A'))},
  riskFactors: {json.dumps(modernization.get('risk_factors', []))},
  layers:      {arch_layers_js},
  phases:      {phases_js},
  microsvcs:   {microservices_js},
  targetStack: {target_stack_js},
  concerns:    {json.dumps(summary.get('tech_debt_concerns', []))},
  dbSchema:       {db_schema_js},
  dataBoundaries: {data_boundaries_js},
  businessLogic:  {business_logic_js},
  blockDiagram:   {block_diagram_js},
  dependencyGraph: {dep_graph_js},
}};

// ----------------------------------------------------------------
// Navigation
// ----------------------------------------------------------------
function switchSection(name, btn) {{
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
  document.getElementById('section-' + name).classList.add('active');
  btn.classList.add('active');
  if (name === 'dataarch') initEntityNetwork();
  if (name === 'howitworks') renderBlockDiagram();
  // Close sidebar on mobile after navigation
  if (window.innerWidth <= 860) closeSidebar();
}}

// Mobile sidebar toggle
function toggleSidebar() {{
  const sb = document.getElementById('sidebar');
  const ov = document.getElementById('sidebar-overlay');
  sb.classList.toggle('open');
  ov.classList.toggle('open');
}}
function closeSidebar() {{
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('sidebar-overlay').classList.remove('open');
}}

// ----------------------------------------------------------------
// Count-up animation helper
// ----------------------------------------------------------------
function animateCount(el, target) {{
  const duration = 900;
  const start = performance.now();
  function step(now) {{
    const progress = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(ease * target).toLocaleString();
    if (progress < 1) requestAnimationFrame(step);
  }}
  requestAnimationFrame(step);
}}

// ----------------------------------------------------------------
// Metric cards
// ----------------------------------------------------------------
const ICON_COLORS = ['#0071e3', '#30d158', '#ff9f0a', '#bf5af2', '#ff453a'];
const ICON_SVGS = [
  '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
  '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>',
  '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/></svg>',
  '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>',
  '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
];

function buildMetrics() {{
  const grid = document.getElementById('metrics-grid');
  const items = [
    {{ label: 'Files Analyzed',      value: DATA.metrics.files,     sub: 'source files parsed' }},
    {{ label: 'Classes Defined',     value: DATA.metrics.classes,   sub: 'across all modules' }},
    {{ label: 'Methods & Functions', value: DATA.metrics.methods,   sub: 'total callables' }},
    {{ label: 'API Endpoints',       value: DATA.metrics.endpoints, sub: 'routes extracted' }},
    {{ label: 'Dead Code Files',     value: DATA.metrics.deadFiles, sub: 'potentially unreferenced' }},
  ];
  grid.innerHTML = items.map((item, i) => `
    <div class="metric-card">
      <div class="metric-icon-wrap" style="background:${{ICON_COLORS[i]}}18;color:${{ICON_COLORS[i]}}">
        ${{ICON_SVGS[i]}}
      </div>
      <div class="metric-label">${{item.label}}</div>
      <div class="metric-value" data-target="${{item.value}}">0</div>
      <div class="metric-sub">${{item.sub}}</div>
    </div>`).join('');
  // Trigger count-up
  document.querySelectorAll('.metric-value[data-target]').forEach(el => {{
    animateCount(el, parseInt(el.dataset.target, 10));
  }});
}}

// ----------------------------------------------------------------
// Language horizontal bar chart
// ----------------------------------------------------------------
const BAR_COLORS = ['#0071e3','#30d158','#ff9f0a','#bf5af2','#ff453a','#5ac8fa','#ff6961'];
function buildLangBars() {{
  const el = document.getElementById('lang-hbar');
  const langs = Object.entries(DATA.languages).sort((a,b) => b[1]-a[1]);
  const max = langs[0]?.[1] || 1;
  el.innerHTML = langs.map(([lang, count], i) => `
    <div class="hbar-row">
      <div class="hbar-lang">${{lang}}</div>
      <div class="hbar-track">
        <div class="hbar-fill" style="width:0%;background:${{BAR_COLORS[i % BAR_COLORS.length]}}"></div>
      </div>
      <div class="hbar-count">${{count}}</div>
    </div>`).join('');
  // Animate widths after paint
  requestAnimationFrame(() => {{
    document.querySelectorAll('.hbar-fill').forEach((bar, i) => {{
      const count = langs[i]?.[1] || 0;
      bar.style.width = Math.round(count / max * 100) + '%';
    }});
  }});
}}

// ----------------------------------------------------------------
// System summary
// ----------------------------------------------------------------
function buildSummary() {{
  document.getElementById('purpose-text').textContent = DATA.purpose;
  document.getElementById('arch-pattern-text').textContent = DATA.archPattern;
  const pColor = {{ HIGH: 'var(--red)', MEDIUM: 'var(--orange)', LOW: 'var(--green)' }}[DATA.priority] || 'var(--red)';
  const pBg    = {{ HIGH: 'rgba(255,69,58,0.10)', MEDIUM: 'rgba(255,159,10,0.10)', LOW: 'rgba(48,209,88,0.10)' }}[DATA.priority] || 'rgba(255,69,58,0.10)';
  document.getElementById('priority-badge').innerHTML =
    `<span class="priority-pill" style="background:${{pBg}};color:${{pColor}}">${{DATA.priority}} Priority</span>`;
  document.getElementById('effort-text').textContent = DATA.effort;
}}

// ----------------------------------------------------------------
// Tech stack
// ----------------------------------------------------------------
function buildTechStack() {{
  const el = document.getElementById('tech-stack-wrap');
  el.innerHTML = DATA.techStack.length
    ? DATA.techStack.map(t => `<span class="badge">${{t}}</span>`).join('')
    : '<span style="font-size:13px;color:var(--text2)">No specific frameworks detected</span>';
}}

// ----------------------------------------------------------------
// Module bars
// ----------------------------------------------------------------
function buildModuleBars() {{
  const el = document.getElementById('modules-bars');
  if (!DATA.topModules.length) {{
    el.innerHTML = '<p style="font-size:13px;color:var(--text2)">No module data available</p>';
    return;
  }}
  const max = DATA.topModules[0].connections || 1;
  el.innerHTML = DATA.topModules.map(m => `
    <div class="mod-row">
      <div class="mod-label">
        <span>${{m.module}}</span><span style="font-weight:600;color:var(--text)">${{m.connections}}</span>
      </div>
      <div class="mod-track">
        <div class="mod-fill" style="width:${{Math.round(m.connections/max*100)}}%"></div>
      </div>
    </div>`).join('');
}}

// ----------------------------------------------------------------
// API endpoints table
// ----------------------------------------------------------------
function buildEndpoints() {{
  const wrap = document.getElementById('endpoints-table-wrap');
  const cnt  = document.getElementById('ep-count');
  if (!DATA.endpoints.length) {{
    wrap.innerHTML = '<p style="font-size:13px;color:var(--text2);padding:8px 0">No API endpoints detected. Routes may use custom patterns not covered by the static extractor.</p>';
    cnt.textContent = '0 endpoints';
    return;
  }}
  cnt.textContent = DATA.endpoints.length + ' endpoint' + (DATA.endpoints.length !== 1 ? 's' : '');
  const rows = DATA.endpoints.map(ep => {{
    const pills = ep.methods.map(m => `<span class="method-pill ${{m}}">${{m}}</span>`).join('');
    return `<tr>
      <td>${{pills}}</td>
      <td><span class="code-mono">${{ep.path}}</span></td>
      <td style="font-family:monospace;font-size:12px;color:var(--text2)">${{ep.handler}}</td>
      <td><span class="code-mono">${{ep.file}}</span></td>
    </tr>`;
  }}).join('');
  wrap.innerHTML = `
    <table class="data-table">
      <thead><tr><th>Method</th><th>Path</th><th>Handler</th><th>File</th></tr></thead>
      <tbody id="api-tbody">${{rows}}</tbody>
    </table>`;
}}

function filterEndpoints(q) {{
  const rows = document.querySelectorAll('#api-tbody tr');
  let visible = 0;
  rows.forEach(row => {{
    const match = row.textContent.toLowerCase().includes(q.toLowerCase());
    row.style.display = match ? '' : 'none';
    if (match) visible++;
  }});
  const cnt = document.getElementById('ep-count');
  if (cnt) cnt.textContent = visible + ' endpoint' + (visible !== 1 ? 's' : '');
}}

// ----------------------------------------------------------------
// Dead code lists
// ----------------------------------------------------------------
function buildDeadCode() {{
  const fl = document.getElementById('dead-files-list');
  const cl = document.getElementById('dead-classes-list');
  fl.innerHTML = DATA.deadFiles.length
    ? DATA.deadFiles.map(f =>
        `<li class="dead-item"><span class="dead-dot" style="background:var(--orange)"></span>${{f}}</li>`
      ).join('')
    : '<li class="dead-item" style="color:var(--green)">No unreferenced files detected</li>';
  cl.innerHTML = DATA.deadClasses.length
    ? DATA.deadClasses.map(d =>
        `<li class="dead-item"><span class="dead-dot" style="background:var(--red)"></span>
         <strong style="color:var(--text)">${{d.class}}</strong>&nbsp;
         <span style="color:var(--text3)">${{d.file}}</span></li>`
      ).join('')
    : '<li class="dead-item" style="color:var(--green)">No unreferenced classes detected</li>';
}}

// ----------------------------------------------------------------
// Architecture layers
// ----------------------------------------------------------------
function buildArchDetails() {{
  const el = document.getElementById('layers-list');
  const ds = document.getElementById('dep-stats');
  if (!el) return;
  el.innerHTML = DATA.layers.length
    ? DATA.layers.map(l => `<span class="layer-chip">${{l}}</span>`).join('')
    : '<span style="font-size:13px;color:var(--text2);padding:8px">No distinct layers inferred from file paths</span>';
  if (ds) {{
    ds.innerHTML = `
      <div class="stat-row"><span class="stat-label">Total Files Analyzed</span><span class="stat-val">${{DATA.metrics.files}}</span></div>
      <div class="stat-row"><span class="stat-label">Total Classes</span><span class="stat-val">${{DATA.metrics.classes}}</span></div>
      <div class="stat-row"><span class="stat-label">Total Methods</span><span class="stat-val">${{DATA.metrics.methods}}</span></div>
      <div class="stat-row"><span class="stat-label">Architecture Pattern</span><span class="stat-val">${{DATA.archPattern}}</span></div>
    `;
  }}
}}

// ----------------------------------------------------------------
// How It Works — block diagram + full business logic
// ----------------------------------------------------------------
let mermaidInited = false;

function buildHowItWorks() {{
  const bl = DATA.businessLogic || {{}};

  // Domain badge
  const domBadge = document.getElementById('hiw-domain-badge');
  if (domBadge) domBadge.textContent = bl.business_domain || 'General Application';

  // What it does — render each paragraph as <p>
  const whatEl = document.getElementById('hiw-what');
  if (whatEl) {{
    const paras = (bl.what_it_does || 'No description available.').split(/\\n\\n+/);
    whatEl.innerHTML = paras.map(p => `<p style="margin:0 0 10px 0">${{p.replace(/[*][*]/g, '')}}</p>`).join('');
  }}

  // Core workflows
  const wfEl = document.getElementById('hiw-workflows');
  if (wfEl) {{
    const workflows = bl.core_workflows || [];
    if (workflows.length) {{
      wfEl.innerHTML = workflows.map((wf, i) => {{
        const steps = (wf.steps || []).map(s => `<li style="margin-bottom:3px">${{s}}</li>`).join('');
        const eps   = (wf.endpoints || []).map(e => `<code style="font-size:11px;background:var(--surface2);padding:2px 6px;border-radius:4px;margin-right:4px">${{e}}</code>`).join('');
        return `
          <div style="margin-bottom:16px;padding:14px;background:var(--surface2);border-radius:8px;border-left:3px solid #0071e3">
            <div style="font-weight:600;font-size:14px;margin-bottom:6px;color:var(--text)">${{i+1}}. ${{wf.name || 'Workflow ' + (i+1)}}</div>
            ${{wf.description ? `<p style="font-size:13px;color:var(--text2);margin:0 0 8px 0">${{wf.description}}</p>` : ''}}
            ${{steps ? `<ul style="margin:0 0 8px 0;padding-left:18px;font-size:13px;color:var(--text)">${{steps}}</ul>` : ''}}
            ${{eps ? `<div style="margin-top:6px">${{eps}}</div>` : ''}}
          </div>`;
      }}).join('');
    }} else {{
      wfEl.innerHTML = '<p style="font-size:13px;color:var(--text2)">No workflows detected</p>';
    }}
  }}

  // User roles
  const rolesEl = document.getElementById('hiw-roles');
  if (rolesEl) {{
    const roles = bl.user_roles || [];
    rolesEl.innerHTML = roles.length
      ? roles.map(r => `<span class="badge green">${{r}}</span>`).join('')
      : '<span style="font-size:13px;color:var(--text2)">No roles detected</span>';
  }}

  // Business rules
  const rulesEl = document.getElementById('hiw-rules');
  if (rulesEl) {{
    const rules = bl.key_business_rules || [];
    rulesEl.innerHTML = rules.length
      ? rules.map(r => `<li style="margin-bottom:5px">${{r}}</li>`).join('')
      : '<li style="color:var(--text2)">No rules inferred</li>';
  }}

  // Entity glossary — data shape: {{entity, business_meaning, key_operations}}
  const entEl = document.getElementById('hiw-entities');
  if (entEl) {{
    const ents = bl.data_entities_explained || [];
    if (ents.length) {{
      entEl.innerHTML = `
        <table style="width:100%;border-collapse:collapse;font-size:13px">
          <thead>
            <tr style="border-bottom:1px solid var(--border)">
              <th style="text-align:left;padding:8px 12px;color:var(--text2);font-weight:500;width:25%">Entity</th>
              <th style="text-align:left;padding:8px 12px;color:var(--text2);font-weight:500">Business Meaning</th>
              <th style="text-align:left;padding:8px 12px;color:var(--text2);font-weight:500;width:30%">Key Operations</th>
            </tr>
          </thead>
          <tbody>
            ${{ents.map((e, i) => `
              <tr style="border-bottom:1px solid var(--border);background:${{i%2===0?'transparent':'var(--surface2)'}}">
                <td style="padding:8px 12px;font-weight:600;color:var(--blue)">${{e.entity || e.name || e}}</td>
                <td style="padding:8px 12px;color:var(--text)">${{e.business_meaning || e.description || e.meaning || ''}}</td>
                <td style="padding:8px 12px;color:var(--text2);font-size:12px">${{(e.key_operations || []).join(', ')}}</td>
              </tr>`).join('')}}
          </tbody>
        </table>`;
    }} else {{
      entEl.innerHTML = '<p style="font-size:13px;color:var(--text2)">No entity glossary available</p>';
    }}
  }}

  // Integrations
  const intEl = document.getElementById('hiw-integrations');
  if (intEl) {{
    const integrations = bl.integrations || [];
    intEl.innerHTML = integrations.length
      ? integrations.map(i => `<span class="badge">${{i}}</span>`).join('')
      : '<span style="font-size:13px;color:var(--text2)">None detected</span>';
  }}
  // NOTE: renderBlockDiagram() is called from switchSection('howitworks')
  // not here, to ensure Mermaid CDN is loaded before rendering.
}}

function renderBlockDiagram() {{
  const container = document.getElementById('block-diagram-graphviz');
  if (!container) return;
  
  const data = DATA.blockDiagram;
  if (!data || !data.layers || !data.layers.length) {{
    container.innerHTML = '<p style="font-size:13px;color:var(--text2);padding:24px">No system architecture block diagram available</p>';
    return;
  }}

  let html = '<div class="block-diagram-wrap" style="width:100%; max-width:800px; display:flex; flex-direction:column; gap:12px; margin:0 auto;">';
  
  data.layers.forEach((layer, idx) => {{
    if (idx > 0) {{
      html += `
        <div class="layer-connector-flow" style="display:flex; flex-direction:column; align-items:center; margin:-6px 0 -6px 0; z-index:1;">
          <div class="connector-line" style="width:2px; height:24px; background:var(--border); transition:background 0.3s;"></div>
          <div class="connector-arrow" style="width:0; height:0; border-left:5px solid transparent; border-right:5px solid transparent; border-top:6px solid var(--border); transition:border-top-color 0.3s;"></div>
        </div>`;
    }}
    
    const nodeChips = layer.nodes.map(node => `
      <div class="diagram-node-pill" 
           id="diagram-node-${{node.id}}" 
           data-node-id="${{node.id}}"
           data-layer-color="${{layer.color}}"
           style="background:var(--surface); border:1.5px solid var(--border); padding:8px 16px; border-radius:8px; font-size:12px; font-weight:550; color:var(--text); cursor:pointer; transition:all 0.25s cubic-bezier(0.4, 0, 0.2, 1); display:flex; align-items:center; gap:6px; user-select:none;">
        <span class="node-dot-indicator" style="width:6px; height:6px; background:${{layer.color}}; border-radius:50%;"></span>
        ${{node.label}}
      </div>
    `).join('');
    
    html += `
      <div class="diagram-layer-card" 
           id="diagram-layer-${{layer.id}}"
           style="border:1px solid var(--border); border-left:5px solid ${{layer.color}}; background:var(--surface1); padding:16px; border-radius:12px; box-shadow:0 4px 12px rgba(0,0,0,0.03); transition:all 0.3s ease;">
        <div class="diagram-layer-header" style="display:flex; align-items:center; margin-bottom:12px;">
          <span style="font-weight:700; font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:${{layer.color}};">${{layer.label}}</span>
        </div>
        <div class="diagram-layer-nodes" style="display:flex; flex-wrap:wrap; gap:8px;">
          ${{nodeChips}}
        </div>
      </div>
    `;
  }});
  
  html += '</div>';
  container.innerHTML = html;
  
  const nodes = container.querySelectorAll('.diagram-node-pill');
  nodes.forEach(nodeEl => {{
    nodeEl.addEventListener('mouseenter', () => {{
      const hoveredId = nodeEl.dataset.nodeId;
      const layerColor = nodeEl.dataset.layerColor;
      
      const connectedIds = new Set();
      
      (data.edges || []).forEach(edge => {{
        if (edge.from === hoveredId) {{
          connectedIds.add(edge.to);
        }} else if (edge.to === hoveredId) {{
          connectedIds.add(edge.from);
        }}
      }});
      
      nodeEl.style.background = layerColor;
      nodeEl.style.borderColor = layerColor;
      nodeEl.style.color = '#ffffff';
      nodeEl.style.transform = 'translateY(-2px) scale(1.03)';
      nodeEl.style.boxShadow = `0 6px 16px ${{layerColor}}33`;
      const dot = nodeEl.querySelector('.node-dot-indicator');
      if (dot) dot.style.background = '#ffffff';
      
      connectedIds.forEach(id => {{
        const connEl = document.getElementById(`diagram-node-${{id}}`);
        if (connEl) {{
          const connColor = connEl.dataset.layerColor;
          connEl.style.borderColor = connColor;
          connEl.style.background = `${{connColor}}12`;
          connEl.style.transform = 'scale(1.02)';
          connEl.style.boxShadow = '0 4px 10px rgba(0,0,0,0.06)';
        }}
      }});
      
      nodes.forEach(otherEl => {{
        const otherId = otherEl.dataset.nodeId;
        if (otherId !== hoveredId && !connectedIds.has(otherId)) {{
          otherEl.style.opacity = '0.35';
        }}
      }});
    }});
    
    nodeEl.addEventListener('mouseleave', () => {{
      nodes.forEach(el => {{
        el.style.background = 'var(--surface)';
        el.style.borderColor = 'var(--border)';
        el.style.color = 'var(--text)';
        el.style.transform = '';
        el.style.boxShadow = '';
        el.style.opacity = '';
        const dot = el.querySelector('.node-dot-indicator');
        if (dot) dot.style.background = el.dataset.layerColor;
      }});
    }});
  }});
}}


// ----------------------------------------------------------------
// Data Architecture — static content (boundary cards, entity table)
// ----------------------------------------------------------------
function buildDataArch() {{
  const schema     = DATA.dbSchema     || {{ entities: [], entity_count: 0, relationship_count: 0 }};
  const boundaries = DATA.dataBoundaries || [];

  // Metric cards
  const dbMetEl = document.getElementById('db-metrics');
  if (dbMetEl) {{
    const dbItems = [
      {{ label: 'Entities Detected',  value: schema.entity_count || 0,       sub: 'tables / domain models',  col: '#0071e3' }},
      {{ label: 'Relationships',      value: schema.relationship_count || 0,  sub: 'FK and navigation links', col: '#30d158' }},
      {{ label: 'Bounded Contexts',   value: boundaries.length,               sub: 'proposed microservices',  col: '#bf5af2' }},
    ];
    dbMetEl.innerHTML = dbItems.map(item => `
      <div class="metric-card">
        <div class="metric-icon-wrap" style="background:${{item.col}}18;color:${{item.col}}">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <ellipse cx="12" cy="5" rx="9" ry="3"/>
            <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
            <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
          </svg>
        </div>
        <div class="metric-label">${{item.label}}</div>
        <div class="metric-value">${{item.value.toLocaleString()}}</div>
        <div class="metric-sub">${{item.sub}}</div>
      </div>`).join('');
  }}

  // Legend inside the entity diagram card
  const legendEl = document.getElementById('entity-legend');
  if (legendEl && boundaries.length) {{
    legendEl.innerHTML = boundaries.slice(0, 6).map(b =>
      `<span><span class="legend-dot" style="background:${{b.color}}"></span>${{(b.name || '').split('/')[0].trim()}}</span>`
    ).join('');
  }}

  // Boundary cards grid
  const bgEl = document.getElementById('boundary-grid');
  if (bgEl) {{
    if (!boundaries.length) {{
      bgEl.innerHTML = '<p style="font-size:13px;color:var(--text2)">No bounded contexts identified.</p>';
    }} else {{
      bgEl.innerHTML = boundaries.map(b => {{
        const chips = (b.entities || []).map(e =>
          `<span class="entity-chip" style="border-color:${{b.color}}55;color:${{b.color}}">${{e}}</span>`
        ).join('');
        const empty = !(b.entities || []).length
          ? '<span style="font-size:11px;color:var(--text3);font-style:italic">From AI modernisation roadmap</span>'
          : '';
        return `
          <div class="boundary-card">
            <div class="boundary-card-header">
              <div class="boundary-dot" style="background:${{b.color}}"></div>
              <div class="boundary-name">${{b.name}}</div>
              <div class="boundary-count">${{b.entity_count || (b.entities || []).length}} entities</div>
            </div>
            <div class="entity-chips">${{chips || empty}}</div>
          </div>`;
      }}).join('');
    }}
  }}

  // Entity table
  const etEl = document.getElementById('entity-table-wrap');
  if (etEl) {{
    const ents = schema.entities || [];
    if (!ents.length) {{
      etEl.innerHTML = [
        '<p style="font-size:13px;color:var(--text2);padding:8px 0;line-height:1.7">',
        'No entity definitions were detected in the parsed files. ',
        'This is expected when entity/model files fall outside the 300-file analysis cap ',
        '(priority goes to controllers, services, and repositories). ',
        'The microservice boundary suggestions above are derived from the AI modernisation roadmap. ',
        'To improve entity detection, run the tool on a smaller repo or add entity files to the priority list.',
        '</p>',
      ].join('');
    }} else {{
      const rows = ents.map(e => {{
        const fCount = (e.fields || []).length;
        const rels   = (e.relationships || []).slice(0, 3).map(r => r.type + ': ' + r.target).join('; ');
        return `<tr>
          <td><span style="font-family:monospace;font-size:12px;font-weight:600;color:var(--text)">${{e.name}}</span></td>
          <td><span class="code-mono">${{e.table}}</span></td>
          <td><span class="badge">${{fCount}} field${{fCount !== 1 ? 's' : ''}}</span></td>
          <td style="font-size:11px;color:var(--text2);max-width:240px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${{rels || '&mdash;'}}</td>
          <td><span class="code-mono">${{e.file}}</span></td>
        </tr>`;
      }}).join('');
      etEl.innerHTML = `<table class="data-table">
        <thead><tr>
          <th>Entity</th><th>Table</th><th>Fields</th><th>Relationships</th><th>File</th>
        </tr></thead>
        <tbody>${{rows}}</tbody>
      </table>`;
    }}
  }}
}}

// ----------------------------------------------------------------
// Data Architecture — interactive entity relationship network
// ----------------------------------------------------------------
let entityNetInited = false;

function initEntityNetwork() {{
  if (entityNetInited) return;
  const wrap      = document.getElementById('entity-net-wrap');
  const container = document.getElementById('entity-network');
  if (!container) return;

  const entities   = (DATA.dbSchema && DATA.dbSchema.entities) ? DATA.dbSchema.entities : [];
  const boundaries = DATA.dataBoundaries || [];

  if (!entities.length) {{
    if (wrap) wrap.style.height = 'auto';
    container.innerHTML = [
      '<p style="padding:32px 24px;font-size:13px;color:var(--text2);line-height:1.7">',
      'No entity definitions detected in the analyzed files. ',
      'Microservice boundary suggestions in the cards below are derived from the AI modernisation roadmap. ',
      'Re-run the tool on a repository where entity/model files are within the 300-file cap to see a live ER diagram.',
      '</p>',
    ].join('');
    entityNetInited = true;
    return;
  }}

  // Build colour map: entity name -> boundary colour
  const colorMap = {{}};
  boundaries.forEach(b => {{
    (b.entities || []).forEach(eName => {{ colorMap[eName] = b.color || '#d1d1d6'; }});
  }});

  const nodeMap  = new Map();
  const nodesArr = [];
  const edgesArr = [];
  let nid = 0;

  entities.forEach(entity => {{
    const col = colorMap[entity.name] || '#aeaeb2';
    const id  = nid++;
    nodeMap.set(entity.name, id);
    nodesArr.push({{
      id,
      label: entity.name,
      title: entity.name + ' (' + (entity.fields || []).length + ' fields, ' + (entity.relationships || []).length + ' rels)',
      color: {{ background: col, border: col, highlight: {{ background: col, border: '#1d1d1f' }} }},
      font:  {{ size: 12, color: '#fff', face: 'Helvetica Neue,Arial,sans-serif', bold: true }},
      shape: 'box', margin: 8, borderWidth: 0,
      shadow: {{ enabled: true, size: 4, x: 2, y: 2, color: 'rgba(0,0,0,0.15)' }},
    }});
  }});

  entities.forEach(entity => {{
    (entity.relationships || []).forEach(rel => {{
      if (nodeMap.has(rel.target)) {{
        edgesArr.push({{
          from:   nodeMap.get(entity.name),
          to:     nodeMap.get(rel.target),
          label:  rel.type,
          arrows: (rel.type === 'one-to-many') ? 'to' : '',
          color:  {{ color: '#c7c7cc', highlight: '#0071e3' }},
          font:   {{ size: 9, color: '#6e6e73', align: 'middle' }},
          width:  1.5,
          smooth: {{ type: 'cubicBezier', roundness: 0.4 }},
        }});
      }}
    }});
  }});

  requestAnimationFrame(() => {{
    try {{
      const net = new vis.Network(
        container,
        {{ nodes: new vis.DataSet(nodesArr), edges: new vis.DataSet(edgesArr) }},
        {{
          physics: {{
            enabled: true,
            solver: 'forceAtlas2Based',
            forceAtlas2Based: {{
              gravitationalConstant: -50, centralGravity: 0.008,
              springLength: 130, springConstant: 0.08, damping: 0.4,
            }},
            stabilization: {{ iterations: 150, updateInterval: 25 }},
          }},
          layout:      {{ improvedLayout: false }},
          interaction: {{ zoomView: true, dragView: true, hover: true, tooltipDelay: 100 }},
          edges:       {{ smooth: {{ type: 'dynamic' }} }},
          nodes:       {{ shadow: {{ enabled: true, size: 4, x: 2, y: 2, color: 'rgba(0,0,0,0.12)' }} }},
        }}
      );
      net.once('stabilizationIterationsDone', () => {{ net.setOptions({{ physics: false }}); }});
      entityNetInited = true;
    }} catch (err) {{
      console.error('Entity network failed:', err);
      container.innerHTML = '<p style="padding:40px 24px;font-size:13px;color:var(--text2)">Entity diagram failed. Check browser console.</p>';
    }}
  }});
}}

// ----------------------------------------------------------------
// Business Logic card (in Overview)
// ----------------------------------------------------------------
function buildBusinessLogic() {{
  const bl = DATA.businessLogic || {{}};

  // Domain badge
  const domainEl = document.getElementById('bl-domain-badge');
  if (domainEl && bl.business_domain) {{
    domainEl.innerHTML = `<span class="badge blue" style="font-size:13px;padding:6px 16px">${{bl.business_domain}}</span>`;
  }}

  // What it does — show first paragraph only in the card
  const whatEl = document.getElementById('bl-what');
  if (whatEl && bl.what_it_does) {{
    const firstPara = bl.what_it_does.split('\\n\\n')[0].replace(/[*][*]/g, '');
    whatEl.textContent = firstPara;
  }}

  // User roles
  const rolesEl = document.getElementById('bl-roles');
  if (rolesEl) {{
    rolesEl.innerHTML = (bl.user_roles || []).length
      ? (bl.user_roles || []).map(r => `<span class="badge green">${{r}}</span>`).join('')
      : '<span style="font-size:13px;color:var(--text2)">Not detected</span>';
  }}

  // Integrations
  const intEl = document.getElementById('bl-integrations');
  if (intEl) {{
    intEl.innerHTML = (bl.integrations || []).length
      ? (bl.integrations || []).map(i => `<span class="badge">${{i}}</span>`).join('')
      : '<span style="font-size:13px;color:var(--text2)">None detected</span>';
  }}

  // Key business rules (first 4)
  const rulesEl = document.getElementById('bl-rules');
  if (rulesEl) {{
    const rules = (bl.key_business_rules || []).slice(0, 4);
    rulesEl.innerHTML = rules.length
      ? rules.map(r => `<li>${{r}}</li>`).join('')
      : '<li style="color:var(--text2)">No rules inferred</li>';
  }}
}}

// ----------------------------------------------------------------
// Boot — render all static sections at startup.
// Sections that rely on external CDNs (Mermaid, vis.js) are
// triggered lazily via switchSection() on first tab activation.
// ----------------------------------------------------------------
buildMetrics();
buildLangBars();
buildSummary();
buildTechStack();
buildModuleBars();
buildBusinessLogic();
buildEndpoints();
buildDeadCode();
buildArchDetails();
buildHowItWorks();   // renders text sections; block diagram deferred to tab click
buildDataArch();     // renders static cards; entity network deferred to tab click
</script>
</body>
</html>"""
    return html
