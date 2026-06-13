---
name: change-impact-analysis
version: 1.0.0
description: >
  Perform a deterministic, graph-driven Change Impact Analysis for a repository.
  Given a set of changed files, builds a dependency graph, finds directly and
  transitively affected modules, validates API contracts for breaking changes,
  parses CODEOWNERS, and computes a 0-100 deployment risk score. Trigger on:
  change impact analysis, analyse this PR, what is affected by this change,
  deployment risk, blast radius, what tests are needed, breaking changes.
author: sarveshtalele
license: MIT
category: software-engineering
tags: [sdlc, dependency-analysis, risk, deployment, code-analysis]
execution:
  type: python-script
  entrypoint: scripts/main.py:run
  timeout_seconds: 110
inputs:
  - name: repo_url
    type: string
    required: false
    description: >
      Public git URL to shallow-clone and analyse (use this from the web).
      Provide repo_url OR repo_path.
    examples: ["https://github.com/pallets/flask"]
  - name: repo_path
    type: string
    required: false
    description: A local repository root the server can read (alternative to repo_url).
  - name: changed_files
    type: array
    items: string
    required: false
    description: Changed file paths relative to the repo root (comma-separated in the UI).
    examples: ["src/flask/app.py"]
  - name: base_branch
    type: string
    required: false
    default: main
    description: Base branch used for API-contract comparison.
outputs:
  - name: impact
    type: object
    description: Direct and transitive impact, impacted APIs, consumers.
  - name: risk
    type: object
    description: Deployment risk score (0-100), level, and recommended action.
  - name: contract_violations
    type: array
    description: Detected breaking API-contract changes.
status: active
---

# Change Impact Analysis Skill

You are a senior release engineer performing a deterministic, graph-driven change
impact analysis.  **You are the AI engine.**  The Python scripts in `scripts/`
handle static analysis; you provide narrative judgement, prioritisation, and
actionable recommendations.

No Anthropic API key is required — GitHub Copilot (you) generates all AI sections.

---

## Step 1 — Identify Changed Files

Ask the user for the list of changed files **if not already provided**.

> **"How should I identify the changed files?"**
> 1. Auto-detect from git (`git diff main...HEAD`) — *(recommended)*
> 2. I'll provide the list manually
> 3. Analyse a specific PR — provide the branch or PR number

If the user chooses option 1 or says nothing specific, use `--from-git`.

If they provide an explicit list, collect the paths.

---

## Step 2 — Ask for Output Location

> **"Where should I save the output files?"**
> 1. `./change-impact-output/` inside the current directory — *(recommended)*
> 2. Directly in the current directory
> 3. A specific path — type it

Map to `--output` flag:
- Option 1 / no answer → omit `--output`
- Option 2 → `--output .`
- Option 3 → `--output <user-supplied-path>`

---

## Step 3 — Run the Analysis Engine

The analysis script is at:
```
.github/skills/change-impact-analysis/scripts/change_impact_skill.py
```

**Check Python is available:**
```bash
python --version
```

**Run the engine:**

```bash
# Option 1 — auto-detect from git
python .github/skills/change-impact-analysis/scripts/change_impact_skill.py \
  --from-git --base-branch main

# Option 2 — explicit file list
python .github/skills/change-impact-analysis/scripts/change_impact_skill.py \
  --changed-files src/api/users.py src/models/user.py src/services/auth.py

# Option 3 — custom output directory
python .github/skills/change-impact-analysis/scripts/change_impact_skill.py \
  --from-git --base-branch main --output ./reports/

# Get raw JSON to stdout (for piping / CI integration)
python .github/skills/change-impact-analysis/scripts/change_impact_skill.py \
  --from-git --json-only
```

Wait for the script to complete.  Output files produced:

| File | Description |
|------|-------------|
| `impact_report.md` | **Primary artifact** — full structured impact report |
| `impact_analysis.json` | Machine-readable result (CI/CD integration) |
| `deployment_checklist.md` | Ready-to-use pre/post deployment checklist |

**If Python or the script is missing**, proceed to [Manual Fallback](#manual-fallback).

---

## Step 4 — Read the Analysis Data

Read the generated files:
```
{output_dir}/impact_report.md
{output_dir}/impact_analysis.json
```

Key fields in `impact_analysis.json` to study:

```json
{
  "impact": {
    "changed_files":           [...],   // normalised paths of changed files
    "impacted_modules":        [...],   // every affected module with type + proximity
    "impacted_apis":           [...],   // API endpoint files in the blast radius
    "regression_areas":        [...],   // high-risk areas to regression-test
    "required_test_suites":    [...],   // unit / integration / e2e suites needed
    "consumer_apps":           [...],   // downstream applications affected
    "direct_impact_count":     N,
    "transitive_impact_count": N
  },
  "contract_violations": [...],         // OpenAPI / GraphQL / Protobuf violations
  "risk": {
    "score":   N,                       // 0–100
    "level":   "LOW|MEDIUM|HIGH|CRITICAL",
    "action":  "...",
    "factors": [...]                    // per-factor breakdown
  }
}
```

Also read:
- [`references/dependency-analysis.md`](references/dependency-analysis.md) — graph algorithm reference
- [`references/risk-scoring.md`](references/risk-scoring.md) — risk factor reference

---

## Step 5 — Provide AI Analysis (You Are the AI Engine)

Think like a senior release engineer who reviewed the complete blast radius.
Produce four AI-quality sections:

---

### 5a — Impact Summary

Write a crisp executive summary (3–5 sentences):
- What changed and why it matters for this release
- Highest-risk modules and why
- Whether this deployment should proceed as-is, needs monitoring, or should be blocked
- One-line recommendation for the release manager

---

### 5b — Blast Radius Explanation

For each **directly changed file**:
1. What does this module do?
2. Which other modules depend on it (transitive chain)?
3. Is there a test that covers this path?
4. What is the worst-case failure mode if this change is faulty?

For the **top 3 highest-risk transitively affected modules**, explain:
- Why they are affected (import chain)
- What would break if the change is incorrect
- Who owns it (from CODEOWNERS / ownership map)

---

### 5c — API Contract Assessment

For each contract violation detected:
1. **What changed** — endpoint / field / type affected
2. **Who is impacted** — which consumers use this endpoint
3. **Migration path** — how consumers should adapt
4. **Recommended action** — deprecate gracefully / block deployment / coordinate release

If no violations: confirm that the API surface is stable and consumers are safe.

---

### 5d — Release Recommendation

Provide a concrete, structured recommendation:

**Verdict:** `PROCEED` / `PROCEED WITH MONITORING` / `BLOCK — REQUIRES REVIEW`

**Rationale:** (2–3 sentences linking the risk score to the specific changes)

**Before deploying:**
- (numbered list of required actions)

**After deploying:**
- (numbered list of verification steps)

**Rollback trigger:** describe the exact condition that should trigger a rollback

---

## Step 6 — Output AI Analysis in Chat

Present the complete analysis in structured markdown:

```
---
## Impact Summary
[Section 5a]

---
## Blast Radius Explanation
[Section 5b]

---
## API Contract Assessment
[Section 5c]

---
## Release Recommendation
[Section 5d]
```

---

## Step 7 — Write AI Content Into Report File

**Do NOT ask** — automatically update the report immediately after the analysis.

Locate the report:
- Default: `./change-impact-output/impact_report.md`
- Custom path: `{output_dir}/impact_report.md`

Append a new section `## AI Release Analysis` at the end of the report containing
all four AI sections.  Use `insert_edit_into_file` to append, or `create_file` to
overwrite if simpler.

Print confirmation:
```
[ok] AI analysis appended to: {report_path}
```

---

## Step 8 — Report Completion

```
Change Impact Analysis complete [ok]

Repository   : {repo_path}
Base branch  : {base_branch}
Changed files: {N}

Risk Score   : {score}/100 — {level}
Action       : {action}

Impact
  Direct modules     : {direct_count}
  Transitive modules : {transitive_count}
  Impacted APIs      : {api_count}
  Consumer apps      : {consumer_count}

Output files in {output_dir}:
  impact_report.md          ← open this first
  impact_analysis.json
  deployment_checklist.md

AI engine: GitHub Copilot (no API key required)
```

---

## Manual Fallback (Script Not Found)

If `change_impact_skill.py` is not found or Python is unavailable:

1. List all source files in the repository:
   ```bash
   git diff --name-only main...HEAD
   ```
   Or ask the user to provide the changed files.

2. For each changed file, use `grep_search` to find all files that import it:
   ```
   Pattern: import.*{module_name}|require.*{module_name}|from.*{module_name}
   ```

3. Repeat for each newly found file (manual BFS, up to 3 hops).

4. Use `file_search` to find `CODEOWNERS` and map files to owners.

5. Use `file_search` to find `openapi.yaml`, `swagger.json`, `*.graphql` for contract checks.

6. Manually calculate risk score using the table in
   [`references/risk-scoring.md`](references/risk-scoring.md).

7. Use [`templates/impact_report.md`](templates/impact_report.md) to produce the report.

8. Write the report to `./impact_report.md`.

9. Continue with Steps 5–8.

---

## Notes

- **No API key required** — GitHub Copilot is the AI engine
- **Deterministic** — given the same inputs the score is always the same
- **Polyglot** — supports Python, JS/TS, Java, C#, Go import graphs
- **CODEOWNERS** — automatically maps every affected file to its owner
- **Contract detection** — OpenAPI, Swagger, GraphQL schema, Protobuf
- **CI/CD ready** — `--json-only` flag emits structured JSON to stdout
- **Script path** — always reference as `.github/skills/change-impact-analysis/scripts/change_impact_skill.py`
