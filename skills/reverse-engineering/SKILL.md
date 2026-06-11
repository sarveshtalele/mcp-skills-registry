---
name: reverse-engineering
version: 1.0.0
description: >
  Reverse-engineer a REMOTE public GitHub repository from its URL. Use this whenever
  you have a github.com URL — it clones the repo server-side and runs static analysis
  (no API keys), producing a System Design Document, architecture + dependency
  overview, auth-pattern detection, business-logic extraction, and a 100-point quality
  score. For a LOCAL filesystem path (not a URL) use the `legacy-discovery` skill
  instead. The returned report is the authoritative analysis — rely on it and do not
  supplement with web search or prior memory. Requires input `repo_url`. Trigger on:
  reverse engineer a GitHub repo, analyse this repo URL, generate an SDD for a repo URL.
author: sarveshtalele
license: MIT
category: software-engineering
tags: [reverse-engineering, architecture, static-analysis, documentation, code-analysis]
execution:
  type: python-script
  entrypoint: scripts/main.py:run
  timeout_seconds: 120
inputs:
  - name: repo_url
    type: string
    required: true
    description: Public GitHub repository URL to analyse.
outputs:
  - name: manifest
    type: object
    description: Run record with metrics and generated-file metadata.
  - name: report_markdown
    type: string
    description: The generated 4-section architectural report (size-capped).
  - name: sdd_available
    type: boolean
    description: Whether a full System Design Document JSON was produced.
status: active
---

# Reverse Engineer a GitHub Repository

You are a senior software architect performing a complete reverse engineering analysis.
**You are the AI engine.** The Python script in `scripts/` handles static analysis;
you provide AI-quality narrative, architectural judgment, and domain explanation.

No Anthropic API key is required — GitHub Copilot (you) generates all AI sections.

The final report has **four sections only**:
1. System Design Overview
2. Authentication & Access Control (RBAC / ABAC / ReBAC)
3. Business Logic Extractor
4. Screen-by-Screen Navigation

---

## Step 1 — Validate Input

The user provides a GitHub repository URL.
Expected format: `https://github.com/owner/repo`

If the URL is missing or malformed, ask:
> **"Please provide a full GitHub repository URL (e.g. https://github.com/django/django)."**

---

## Step 2 — Ask for Output Location

Before running the analysis, ask:

> **"Where should I save the output files?**
> 1. A folder named after the repo in the current directory — e.g. `./nopCommerce/` _(recommended)_
> 2. Directly in the current directory — files land next to your code
> 3. A specific path — type it (e.g. `C:\Reports` or `~/analysis`)"

If the user does not answer or presses Enter, default to **option 1**.

Map the answer to a `--output` flag:
- Option 1 / no answer → omit `--output` (script creates `./{repo_name}/`)
- Option 2 → `--output .`
- Option 3 → `--output <user-supplied-path>`

---

## Step 3 — Run the Static Analysis Engine

The analysis script is bundled with this skill at:
```
.github/skills/reverse-engineering-skill/scripts/reverse_engineer_skill.py
```

**Check Python is available:**
```bash
python --version
```

**Run the engine** (substitute `<URL>` and the output flag from Step 2):
```bash
# Option 1 — default subfolder
python .github/skills/reverse-engineering-skill/scripts/reverse_engineer_skill.py <URL> --heuristic

# Option 2 — current directory
python .github/skills/reverse-engineering-skill/scripts/reverse_engineer_skill.py <URL> --heuristic --output .

# Option 3 — custom path
python .github/skills/reverse-engineering-skill/scripts/reverse_engineer_skill.py <URL> --heuristic --output <PATH>
```

Wait for completion. Output files produced:

| File | Description |
|------|-------------|
| `{repo}_report.md` | **4-section focused report** — primary artifact |
| `{repo}_sdd.json` | Full System Design Document (JSON) |
| `{repo}_dashboard.html` | Self-contained interactive dashboard |
| `{repo}_block_diagram.svg` | Architecture layers diagram |
| `{repo}_dependency_graph.svg` | Module dependency graph |
| `{repo}_evaluation.md` | 100-point quality score |
| `manifest.json` | Run metrics |

**If the script is not found**, go to [Manual Fallback](#manual-fallback-script-not-found) at the bottom.

---

## Step 4 — Read the Analysis Data

Read the SDD JSON (contains all static-analysis results):
```
{output_path}/{repo_name}/{repo_name}_sdd.json
```
Also read the generated report skeleton:
```
{output_path}/{repo_name}/{repo_name}_report.md
```

Key SDD sections to study:
- `project` — language, tech_stack, platform, layers
- `codebase_metrics` — file / class / method / endpoint counts
- `api_catalog` — all extracted API endpoints
- `data_architecture` — ORM entities, relationships, microservice boundaries
- `business_logic` — domain, workflows, roles, rules (heuristic draft; you will enhance)
- `auth_analysis` — RBAC / ABAC / ReBAC findings, roles, policies, route map
- `screens_navigation` — screen inventory and navigation flow
- `modernization_roadmap` — phased plan, target stack, effort estimate

Also read relevant source files from the `references/` folder:
- [`references/ARCHITECTURE.md`](references/ARCHITECTURE.md) — how the engine works
- [`references/AUTH_PATTERNS.md`](references/AUTH_PATTERNS.md) — auth detection reference

---

## Step 5 — Provide AI Analysis (You Are the AI Engine)

Think like a senior architect who reviewed the complete codebase.
Produce AI-quality narrative for all four sections.

---

### 5a · Section 1 — System Design Overview

Provide a complete architectural picture:

**Executive Summary**
- What does this system do and for whom? (2–3 sentences)
- Architecture pattern (e.g. "Layered N-Tier MVC Monolith with ASP.NET Web Forms")
- Top 3 tech-debt concerns visible from structure
- Modernization priority (HIGH / MEDIUM / LOW) + reasoning

**How the system is structured end-to-end:**
- Client → Controller/Handler → Service → Repository → Database
- Name the actual classes and files for each layer
- Data flow: request path from user action to DB and back

**Key components and responsibilities** — name real classes/files

**External integrations** — payment, email, cache, auth providers detected

**Deployment model** — monolith / microservices / serverless inferred from structure

---

### 5b · Section 2 — Authentication & Access Control

Analyse and explain the auth model found in the code:

1. **Auth Model in Use** — Is this RBAC, ABAC, ReBAC, or a hybrid?
2. **RBAC** (if present):
   - Which roles exist? (list named roles from code)
   - Where are roles checked? (annotated controllers, middleware, guards)
   - Example quote: "`Admin` role enforced on `/admin/*` via `[Authorize(Roles=\"Admin\")]`"
3. **ABAC** (if present):
   - Which policies are defined?
   - What claims or attributes are evaluated?
4. **ReBAC** (if present):
   - What resource relationships are checked?
   - Example: "`IsOwner()` in `OrderService` — users can only edit their own orders"
5. **Auth Gaps / Security Observations**:
   - Unguarded routes that look sensitive
   - Is auth strategy consistent or ad-hoc?

---

### 5c · Section 3 — Business Logic Extractor

1. **Business Domain** — e.g. "E-Commerce Platform", "HR System"
2. **What It Does** — 3–4 paragraphs for non-technical stakeholders
3. **Core Workflows** (4–6 workflows, each covering):
   - Trigger (user action or event)
   - Steps through the system (controller → service → repo → DB)
   - Business rules enforced
   - Endpoints involved
4. **User Roles & What They Can Do** — one bullet per role
5. **Key Business Rules** — validation, constraints, ownership, lifecycle
6. **Entity Glossary** — plain-English meaning per data entity
7. **Why This System Exists** — the business problem it solves

---

### 5d · Section 4 — Screen-by-Screen Navigation

Complete end-to-end navigation guide for the application UI:

1. **Project Type** — e.g. "ASP.NET Web Forms", "MVC + Razor Views", "React SPA"
2. **Screen Inventory** — for each screen:
   - Name and purpose
   - What the user sees
   - Available actions
   - Data displayed (entities)
   - Who can access (role)
   - How to reach this screen (navigation in)
   - Where to go next (navigation out)
3. **Complete Navigation Flow**:
   - Unauthenticated path: Landing → Login/Register → Redirect
   - Authenticated path: Dashboard → workflows → completion
   - Admin path: Admin Panel → management → reports
4. **Screen Transitions** — what triggers each navigation (button, form submit, redirect, auto)
5. **Error/Exception Screens** — 404, Unauthorized, validation failure screens

---

## Step 6 — Output AI Analysis in Chat

Present the complete analysis in structured markdown:

```
---
## System Design Overview
[Section 1 analysis]

---
## Authentication & Access Control
[Section 2 analysis]

---
## Business Logic Extractor
[Section 3 analysis]

---
## Screen-by-Screen Navigation
[Section 4 analysis]
```

---

## Step 7 — Write AI Content Into Report File

**Do NOT ask the user** — automatically update the report immediately.

Locate the report file:
- Default (option 1): `./{repo_name}/{repo_name}_report.md`
- Current dir (option 2): `./{repo_name}_report.md`
- Custom path (option 3): `{custom_path}/{repo_name}/{repo_name}_report.md`

Edit the file to replace each of the four sections with your AI-enhanced version.

Use `insert_edit_into_file` to replace section-by-section or `create_file` to overwrite if simpler.

Print confirmation:
```
✓ AI analysis written to: {report_path}
```

---

## Step 8 — Report Completion

```
Reverse engineering complete ✓
Repository : {repo_url}
Report     : {report_path}

Sections generated:
  ✓ 1. System Design Overview
  ✓ 2. Authentication & Access Control (RBAC / ABAC / ReBAC)
  ✓ 3. Business Logic Extractor
  ✓ 4. Screen-by-Screen Navigation

Stats:
  Files: {N} | Classes: {N} | Methods: {N} | Endpoints: {N}
  Auth model: {type} | Screens: {N}
  AI engine: GitHub Copilot (no API key required)

Other output files in {output_dir}:
  {repo}_sdd.json            — Full System Design Document
  {repo}_dashboard.html      — Interactive stakeholder dashboard
  {repo}_block_diagram.svg   — Architecture diagram
  {repo}_dependency_graph.svg
  {repo}_evaluation.md
  manifest.json
```

---

## Manual Fallback (Script Not Found)

If `python .github/skills/reverse-engineering-skill/scripts/reverse_engineer_skill.py` is missing:

```bash
git clone --depth=1 <URL> ./temp_analysis_repo
```

Discover files: `.py .java .cs .ts .tsx .js .jsx .aspx .aspx.cs .cshtml .html .vue`
Skip: `node_modules/ bin/ obj/ .git/ dist/ build/ migrations/ __pycache__/`

For each file extract:
- Classes, methods, imports, API routes, ORM entities
- Auth annotations: `[Authorize]`, `@PreAuthorize`, `@login_required`, `Policy=`
- Screen files: `.aspx`, `.cshtml`, `.jsx`, `.vue`, `.html`

Use the template at [`templates/report_template.md`](templates/report_template.md) to produce the output.

Write report to the user-selected output location (Step 2).

Then continue with Steps 5–8.

---

## Notes

- **No API key required** — GitHub Copilot is the AI engine
- **Output location** — files go to the user's chosen directory (Step 2), not a hidden `outputs/` folder
- **Script path** — always reference as `.github/skills/reverse-engineering-skill/scripts/reverse_engineer_skill.py`
- **ASPX support** — `.aspx` and `.aspx.cs` are Web Forms screens; detected automatically
- **File cap** — up to 300 files, layer-balanced (controllers → services → repos → domain → models)
- **Auth detection** — RBAC, ABAC, ReBAC patterns across C# / Java / Python / JS / TS
