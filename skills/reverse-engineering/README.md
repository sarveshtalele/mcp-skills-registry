# How to Install & Use This Skill

## What You Get

A GitHub Copilot Agent Skill that reverse engineers any GitHub repository and produces a focused 4-section report:

| # | Section |
|---|---------|
| 1 | **System Design Overview** — full architecture, metrics, API catalog, data model |
| 2 | **Authentication & Access Control** — detects RBAC / ABAC / ReBAC |
| 3 | **Business Logic Extractor** — domain, workflows, rules, entity glossary |
| 4 | **Screen-by-Screen Navigation** — complete UI journey (supports ASPX, Razor, React, Vue) |

No API key required. GitHub Copilot is the AI engine.

---

## Requirements

| Tool | Version |
|------|---------|
| VS Code | 1.90 or later |
| GitHub Copilot Chat extension | latest |
| Python | 3.8 or later |
| Git | any version, must be on PATH |

---

## Installation (one-time, 2 minutes)

### Step 1 — Copy the skill folder into your project

```
Your project/
└── .github/
    └── skills/
        └── reverse-engineering-skill/   ← paste this folder here
```

If `.github/skills/` doesn't exist yet, create it.

### Step 2 — Verify Python is installed

```bash
python --version
# Should print Python 3.8 or higher
```

### Step 3 — Done. Open Copilot Chat and use the skill.

---

## Usage in VS Code

1. Open your project in VS Code
2. Open GitHub Copilot Chat (`Ctrl+Alt+I` / `Cmd+Alt+I`)
3. Type the repo URL:

```
Reverse engineer https://github.com/owner/repo
```

Copilot will:
- Ask where to save the output files
- Run the Python analysis engine automatically
- Produce AI-quality narrative for all 4 sections
- Write the final report directly to your chosen location

---

## Where Output Files Land

By default, output is written to `./{repo-name}/` inside your current working directory:

```
your-project/
└── nopCommerce/           ← created automatically
    ├── nopCommerce_report.md      ← 4-section focused report  ← open this first
    ├── nopCommerce_sdd.json       ← full system design doc (JSON)
    ├── nopCommerce_dashboard.html ← interactive HTML dashboard
    ├── nopCommerce_block_diagram.svg
    ├── nopCommerce_dependency_graph.svg
    ├── nopCommerce_evaluation.md
    └── manifest.json
```

You can also say:
- **"save in current folder"** → files land next to your project files
- **"save to C:\Reports"** → writes to a custom path

---

## Running Without Copilot (CLI Only)

```bash
# Default output → ./{repo-name}/ in current directory
python .github/skills/reverse-engineering-skill/scripts/reverse_engineer_skill.py \
    https://github.com/owner/repo --heuristic

# Output directly to current directory
python .github/skills/reverse-engineering-skill/scripts/reverse_engineer_skill.py \
    https://github.com/owner/repo --heuristic --output .

# Custom output folder
python .github/skills/reverse-engineering-skill/scripts/reverse_engineer_skill.py \
    https://github.com/owner/repo --heuristic --output C:\Reports
```

---

## Sharing With Your Team

- Commit the `reverse-engineering-skill/` folder inside `.github/skills/` to your repo
- Every developer on the team gets the skill automatically when they pull
- No additional setup required for team members who already have Copilot + Python
