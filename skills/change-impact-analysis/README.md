# Change Impact Analysis Skill

> **Graph-driven · Deterministic · Deployment-phase intelligence**  
> Works with **GitHub Copilot**, **Claude Code**, and **Cursor**

A polyglot agent skill that answers the question every engineer asks before deploying:
*"What will break, who owns it, and should we ship this?"*

---

## Why This Skill Exists

Code review catches bugs. Test suites catch regressions. But neither tells you:

- Which modules are *transitively* affected by your changes (N hops away in the import graph)?
- Whether any API contracts are broken for downstream consumers?
- What the *deployment risk score* is — a single number your release manager can act on?
- Who to notify before you deploy?

| Property | Description |
|----------|-------------|
| **Deterministic** | Same inputs → same outputs, every time. No randomness. |
| **Explainable** | Every affected file has a traceable import-chain path back to the change. |
| **Transitive** | Catches indirect dependencies that code review always misses. |
| **Polyglot** | Python, JavaScript/TypeScript, Java, C#, Go. |
| **Fast** | Sub-second BFS on an in-memory graph, even at 100k files. |

---

## Folder Structure

```
change-impact-analysis/
├── assets/
│   ├── architecture-diagram.svg    ← Architecture diagram
│   └── requirements.txt            ← Python dependencies (PyYAML optional)
│
├── references/
│   ├── dependency-analysis.md      ← Graph algorithm reference
│   └── risk-scoring.md             ← Risk factor breakdown & examples
│
├── scripts/
│   ├── change_impact_skill.py      ← CLI entry point / orchestrator
│   └── engine/
│       ├── __init__.py
│       ├── graph_builder.py        ← AST-based dependency graph construction
│       ├── impact_analyzer.py      ← Reverse-BFS blast-radius computation
│       ├── risk_scorer.py          ← Deterministic 0-100 scoring model
│       ├── contract_validator.py   ← OpenAPI / GraphQL / Protobuf validation
│       ├── ownership_parser.py     ← CODEOWNERS / package.json parsing
│       └── report_generator.py     ← Markdown + JSON + checklist output
│
├── templates/
│   ├── impact_report.md            ← Report template
│   └── deployment_checklist.md     ← Checklist template
│
├── DOCUMENTATION.md                ← Complete technical documentation
├── INSTALL.md                      ← Setup and installation guide
├── README.md                       ← This file
└── SKILL.md                        ← Agent skill definition
```

---

## Requirements

| Tool | Version |
|------|---------|
| Python | 3.8 or later |
| Git | Any version (must be on PATH) |
| PyYAML | Optional — enables YAML spec parsing (`pip install PyYAML`) |

---

## Setup — GitHub Copilot

### Step 1 — Copy the skill into your project

```
your-project/
└── .github/
    └── skills/
        └── change-impact-analysis/   ← paste this folder here
```

### Step 2 — Verify Python

```bash
python --version   # needs 3.8+
```

### Step 3 — Open Copilot Chat and trigger

Open GitHub Copilot Chat (`Ctrl+Alt+I` / `Cmd+Alt+I`) and type any of these:

```
Analyse the change impact for this PR
What is the deployment risk score?
What tests do I need to run before deploying?
Who owns the code I just changed?
Is it safe to deploy?
What APIs are broken by my changes?
What will break if I change this file?
```

**How it works:**
Copilot reads the `description:` field in `SKILL.md` to recognise your intent, then follows the 8-step workflow — asks where to save output, runs the Python engine in your terminal, reads the JSON result, writes an AI narrative, and prints a final summary.

### Copilot CLI usage

```bash
# Auto-detect from git
python .github/skills/change-impact-analysis/scripts/change_impact_skill.py \
  --from-git --base-branch main

# Explicit files
python .github/skills/change-impact-analysis/scripts/change_impact_skill.py \
  --changed-files src/api/users.py src/models/user.py

# JSON only (for CI gates)
python .github/skills/change-impact-analysis/scripts/change_impact_skill.py \
  --from-git --json-only
```

---

## Setup — Claude Code

### Step 1 — Copy the skill into `.claude/skills/`

Place the skill folder inside your project's `.claude/skills/` directory:

```
your-project/
└── .claude/
    └── skills/
        └── change-impact-analysis/   ← paste this folder here
            ├── SKILL.md
            ├── scripts/
            │   ├── change_impact_skill.py
            │   └── engine/
            ├── assets/
            ├── references/
            └── templates/
```

> **Why `.claude/skills/`?**  
> Claude Code automatically discovers skills placed here. The `SKILL.md` file is
> read as the skill definition — no commands or config files needed.

### Step 2 — Verify Python

```bash
python --version   # needs 3.8+
```

### Step 3 — Use in Claude Code

Claude Code picks up the skill automatically from `.claude/skills/`. Just type
naturally in the chat panel:

```
Analyse the change impact for this PR
What is the deployment risk score for my changes?
What will break if I deploy this?
What tests do I need to run before deploying?
Who owns the affected code?
Is it safe to deploy on this branch?
Run change impact analysis --from-git
```

**Option A — Natural language (skill auto-activates):**
```
What will break if I deploy my current changes?
```

**Option B — Explicit skill invocation:**
```
/change-impact-analysis
```

**Option C — Reference the skill file directly:**
```
@.claude/skills/change-impact-analysis/SKILL.md
Analyse the change impact for my current branch
```

**Option D — Run the CLI from Claude Code terminal:**
```bash
python .claude/skills/change-impact-analysis/scripts/change_impact_skill.py \
  --from-git --base-branch main

# Explicit files
python .claude/skills/change-impact-analysis/scripts/change_impact_skill.py \
  --changed-files src/api/users.py src/models/user.py

# JSON only (CI gates)
python .claude/skills/change-impact-analysis/scripts/change_impact_skill.py \
  --from-git --json-only
```

**How it works:**
Claude Code reads `SKILL.md` from `.claude/skills/change-impact-analysis/` as the
skill instruction set. It runs the Python engine via its terminal capability, reads
the JSON output, and delivers the AI-enriched impact narrative in chat — no slash
commands or config files required.

---

## Setup — Cursor

### Step 1 — Copy the skill into your project

```
your-project/
└── .github/
    └── skills/
        └── change-impact-analysis/   ← paste this folder here
```

### Step 2 — Create a Cursor Rule

Create `.cursor/rules/change-impact-analysis.mdc` in your project:

````markdown
---
description: Change Impact Analysis — deployment risk, blast radius, affected modules
alwaysApply: false
---

When the user asks about:
- change impact, deployment risk, blast radius
- what will break, safe to deploy, affected modules
- which tests to run, who to notify, API contract changes

Follow the workflow in `.github/skills/change-impact-analysis/SKILL.md` exactly.

Run the engine:
```bash
python .github/skills/change-impact-analysis/scripts/change_impact_skill.py \
  --from-git --base-branch main
```

Read the output from `./change-impact-output/impact_analysis.json` and provide
a full AI-enriched analysis with risk score, blast radius, and release recommendation.
````

### Step 3 — Use in Cursor Chat

**Option A — @-attach the skill file:**
```
@SKILL.md  Analyse the change impact for my PR
```

**Option B — Natural language (rule activates automatically):**
```
What is the deployment risk for my current changes?
Run a change impact analysis
What will break if I deploy this?
```

**Option C — @-attach + run terminal:**
In Cursor Chat, click the `+` button → attach `.github/skills/change-impact-analysis/SKILL.md` → type your request.

**Option D — Use Cursor Terminal directly:**
```bash
python .github/skills/change-impact-analysis/scripts/change_impact_skill.py \
  --from-git --base-branch main
```

**How it works:**
Cursor reads the `.mdc` rule file when your message matches the trigger topics. It then follows the `SKILL.md` instructions — running the Python engine in its integrated terminal, reading the JSON output, and generating an AI response with full impact analysis.

---

## Tool Comparison

| Feature | GitHub Copilot | Claude Code | Cursor |
|---------|---------------|-------------|--------|
| Skill folder location | `.github/skills/change-impact-analysis/` | `.claude/skills/change-impact-analysis/` | `.github/skills/change-impact-analysis/` |
| Trigger method | Natural language (SKILL.md description field) | Natural language · `/change-impact-analysis` · `@SKILL.md` | `.mdc` rule auto-trigger · `@SKILL.md` |
| Config required | None — `SKILL.md` frontmatter is enough | None — drop folder in `.claude/skills/` | `.cursor/rules/change-impact-analysis.mdc` |
| Runs Python engine | Yes — `run_in_terminal` | Yes — terminal tool | Yes — terminal |
| AI narrative | Copilot generates | Claude generates | Cursor AI generates |
| CLI standalone | Yes | Yes | Yes |
| No API key needed | Yes | Yes | Yes |

---

## Output Files

Every run (via any tool) produces:

```
change-impact-output/
├── impact_report.md          ← Open this first — full structured report
├── impact_analysis.json      ← Machine-readable (CI/CD integration)
└── deployment_checklist.md   ← Pre/post deploy sign-off checklist
```

---

## Risk Score Quick Reference

| Score | Level | Action |
|-------|-------|--------|
| 0–30 | **LOW** | Standard release pipeline |
| 31–60 | **MEDIUM** | Deploy with monitoring; notify on-call |
| 61–80 | **HIGH** | Senior review + rollback plan required |
| 81–100 | **CRITICAL** | Block deployment; tech lead escalation |

Six factors drive the score: change volume · transitive spread · API contract violations ·
module type risk · code sensitivity · consumer breadth.

See [`references/risk-scoring.md`](references/risk-scoring.md) for the full breakdown.

---

## Agent Examples

### Example 1 — Feature Branch Analysis

```
I'm about to merge my feature branch. Can you do a change impact analysis?
```

```
Risk Score   : 42/100 — MEDIUM
Action       : Deploy with monitoring. Notify on-call team.

Changed files (3):
  src/services/user_service.py
  src/repositories/user_repo.py
  src/api/users_controller.py

Transitively affected (8 modules):
  src/api/orders_controller.py  [api_endpoint] — imports user_service
  tests/test_users.py           [test]
```

---

### Example 2 — Database Migration Risk

```
Run change impact analysis for: src/db/migrations/0042_users.sql
```

```
Risk Score : 78/100 — HIGH
Action     : Senior engineer review + rollback plan required.

Risk Factors:
  database_schema_change  +10
  api_surface_change      + 6
  transitive_spread       +14  (22 modules affected)
  change_volume           + 8
```

---

### Example 3 — CI/CD Risk Gate

```yaml
# GitHub Actions
- name: Change Impact Gate
  run: |
    SCORE=$(python .github/skills/change-impact-analysis/scripts/change_impact_skill.py \
      --from-git --json-only \
      | python -c "import sys,json; print(json.load(sys.stdin)['risk']['score'])")
    if [ "$SCORE" -gt "80" ]; then
      echo "CRITICAL risk ($SCORE/100) — deployment blocked"
      exit 1
    fi
```

---

### Example 4 — Ownership Query

```
Who owns the code I just changed? I need to notify them before deploying.
```

```
Owner Notifications:
  @payments-team   →  src/services/billing.py
  @platform-team   →  src/core/database.py
  @frontend-guild  →  src/components/UserCard.tsx
```

---

## Architecture

See [`assets/architecture-diagram.svg`](assets/architecture-diagram.svg) for the
architecture diagram.

For complete technical documentation of every component, see [`DOCUMENTATION.md`](DOCUMENTATION.md).

---

