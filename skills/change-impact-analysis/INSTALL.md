# How to Install & Use This Skill

## What You Get

A GitHub Copilot Agent Skill for the **Deployment / Release** SDLC phase that
performs deterministic, graph-driven change impact analysis on any repository.

| Output | Description |
|--------|-------------|
| **Impact Report** | Full structured analysis — impacted modules, APIs, regression areas |
| **Risk Score** | 0–100 deployment risk score: LOW / MEDIUM / HIGH / CRITICAL |
| **Required Tests** | Per-module test suite recommendations |
| **Consumer Apps** | Downstream applications in the blast radius |
| **API Violations** | OpenAPI / GraphQL / Protobuf breaking changes detected |
| **Deploy Checklist** | Ready-to-use pre/post deployment sign-off checklist |

No API key required. GitHub Copilot is the AI engine.

---

## Requirements

| Tool | Version | Required |
|------|---------|----------|
| VS Code | 1.90+ | ✓ |
| GitHub Copilot Chat extension | latest | ✓ |
| Python | 3.8+ | ✓ |
| Git | any (must be on PATH) | ✓ |
| PyYAML | 6.0+ | Optional (enables YAML spec parsing) |

---

## Installation (one-time, ~2 minutes)

### Step 1 — Copy the skill folder into your project

```
your-project/
└── .github/
    └── skills/
        └── change-impact-analysis/   ← paste this folder here
```

If `.github/skills/` doesn't exist, create it.

### Step 2 — Verify Python is installed

```bash
python --version
# Should print Python 3.8 or higher
```

### Step 3 — (Optional) Install PyYAML for YAML spec support

```bash
pip install PyYAML
# or
pip install -r .github/skills/change-impact-analysis/assets/requirements.txt
```

Without PyYAML, the skill still works fully — it just skips YAML-format
OpenAPI specs (JSON specs are always parsed).

### Step 4 — Done. Open Copilot Chat and use the skill.

---

## Usage in VS Code

1. Open your project in VS Code
2. Open GitHub Copilot Chat (`Ctrl+Alt+I` / `Cmd+Alt+I`)
3. Trigger the skill with any of these phrases:

```
Analyse the change impact for this PR
What is the deployment risk score for these changes?
What tests are needed before I deploy?
Who owns the code affected by this change?
Is it safe to deploy?
Run change impact analysis --from-git
What APIs are broken by my changes?
```

Copilot will:
- Ask where to save output (or use the default `./change-impact-output/`)
- Run the Python analysis engine
- Provide AI-quality narrative for all impact dimensions
- Write the final report and checklist to your chosen location

---

## Where Output Files Land

Default output: `./change-impact-output/` inside your project root

```
your-project/
└── change-impact-output/
    ├── impact_report.md          ← open this first
    ├── impact_analysis.json      ← machine-readable (CI/CD)
    └── deployment_checklist.md   ← sign-off checklist
```

You can also say:
- **"save in current folder"** → files land next to your project files
- **"save to C:\Reports"** → writes to a custom path

---

## Running Without Copilot (CLI / CI)

```bash
# Auto-detect changes from git (recommended)
python .github/skills/change-impact-analysis/scripts/change_impact_skill.py \
  --from-git --base-branch main

# Explicit file list
python .github/skills/change-impact-analysis/scripts/change_impact_skill.py \
  --changed-files src/api/users.py src/models/user.py

# Custom repo path and output
python .github/skills/change-impact-analysis/scripts/change_impact_skill.py \
  --repo-path /path/to/repo --from-git --output /tmp/impact-report

# JSON-only (stdout) — pipe into CI gates
python .github/skills/change-impact-analysis/scripts/change_impact_skill.py \
  --from-git --json-only | jq '.risk.score'
```

## CI/CD Integration Example (GitHub Actions)

```yaml
- name: Change Impact Analysis
  run: |
    SCORE=$(python .github/skills/change-impact-analysis/scripts/change_impact_skill.py \
      --from-git --json-only | python -c "import sys,json; print(json.load(sys.stdin)['risk']['score'])")
    echo "Risk score: $SCORE"
    if [ "$SCORE" -gt "80" ]; then
      echo "::error::Deployment risk CRITICAL ($SCORE/100). Human review required."
      exit 1
    fi
```

---

## Sharing With Your Team

- Commit the `change-impact-analysis/` folder to `.github/skills/`
- Every developer gets the skill automatically on pull
- No additional setup for team members who already have Copilot + Python
