# Change Impact Analysis Skill — Technical Documentation

## Table of Contents

1. [Overview & Design Philosophy](#1-overview--design-philosophy)
2. [Architecture](#2-architecture)
3. [SKILL.md — The Agent Brain](#3-skillmd--the-agent-brain)
4. [Script: change_impact_skill.py — Orchestrator](#4-script-change_impact_skillpy--orchestrator)
5. [Engine: graph_builder.py — Dependency Graph](#5-engine-graph_builderpy--dependency-graph)
6. [Engine: impact_analyzer.py — Blast Radius](#6-engine-impact_analyzerpy--blast-radius)
7. [Engine: risk_scorer.py — Risk Scoring](#7-engine-risk_scorerpy--risk-scoring)
8. [Engine: contract_validator.py — API Contracts](#8-engine-contract_validatorpy--api-contracts)
9. [Engine: ownership_parser.py — Code Ownership](#9-engine-ownership_parserpy--code-ownership)
10. [Engine: report_generator.py — Output Generation](#10-engine-report_generatorpy--output-generation)
11. [Templates](#11-templates)
12. [End-to-End Data Flow](#12-end-to-end-data-flow)
13. [Configuration & Extension](#13-configuration--extension)
14. [CI/CD Integration](#14-cicd-integration)

---

## 1. Overview & Design Philosophy

### Problem Statement

Every release engineer faces the same question before deploying: *"What could break,
and should we ship this?"*  Static type-checking and unit tests answer whether code
is *correct*; they do not answer whether a change is *safe to deploy* in the context
of the full dependency graph, downstream consumers, and API contracts.

### Core Design Principles

**Determinism First**
Every output — the dependency graph, the impact list, the risk score — is a pure
function of the repository state.  The same input always produces the same output.
There is no randomness, no heuristic weighting that shifts over time.

**Graph-Driven Analysis**
The dependency graph is the foundation.  Import statements create edges; a change
to any node propagates risk backwards along every reverse edge.  This is the same
model used by Google's Bazel and Meta's Buck build systems for incremental builds —
applied here to release safety instead of compilation.

**Explainability**
Every affected file has a traceable import-chain path back to the change.  The risk
score is broken down factor-by-factor.  The agent can always answer *"why is this
file affected?"* with a concrete chain.

**Zero External Dependencies (Core)**
The core analysis engine uses only the Python standard library (`ast`, `re`,
`pathlib`, `json`).  The single optional dependency (`PyYAML`) unlocks YAML spec
parsing.  No database, no external API, no network call required.

---

## 2. Architecture

```
INPUTS                   ANALYSIS ENGINE                    OUTPUTS
──────                   ───────────────                    ───────
Changed Files    ──▶    graph_builder.py   ──▶    impact_report.md
Dependency Graph         impact_analyzer.py         impact_analysis.json
API Contracts    ──▶    contract_validator.py ──▶   deployment_checklist.md
Deploy Manifests         risk_scorer.py
Ownership Data   ──▶    ownership_parser.py ──▶    Risk Score (0-100)
                         report_generator.py         Required Test Suites
                                                     Consumer Apps
                              ↕
                   change_impact_skill.py
                      (orchestrator CLI)
                              ↕
                     SKILL.md frontmatter
                   (GitHub Copilot trigger)
```

The skill operates in two layers:

**Static Analysis Layer (Python)** — pure computation, no AI:
- Builds the dependency graph
- Computes the blast radius
- Scores risk deterministically
- Generates structured output files

**AI Narrative Layer (GitHub Copilot)** — contextual intelligence:
- Explains *why* affected modules matter
- Prioritises risk factors for the release manager
- Recommends test strategies
- Provides the release verdict

---

## 3. SKILL.md — The Agent Brain

**File:** `SKILL.md`

The SKILL.md file is the GitHub Copilot agent skill definition.  It serves
simultaneously as:

1. **Trigger matcher** — the `description:` frontmatter field is used by
   Copilot to recognise when this skill should be invoked.  It contains a
   comprehensive set of trigger phrases.

2. **System prompt** — the body of the file is the instruction set for the
   Copilot agent.  It defines an 8-step workflow from input validation through
   to final report generation.

3. **Tool manifest** — the `tools:` frontmatter field declares which VS Code
   tools the agent is allowed to invoke (`run_in_terminal`, `read_file`, etc.).

### Frontmatter Schema

```yaml
name: change-impact-analysis       # Unique skill identifier
description: >                     # Trigger phrase index (multiline)
  ...trigger phrases...
version: "1.0.0"
tools:
  - run_in_terminal                 # Execute the Python engine
  - read_file                       # Read analysis output
  - create_file                     # Write reports
  - insert_edit_into_file           # Append AI content to reports
  - file_search                     # Locate CODEOWNERS, specs
  - grep_search                     # Manual import tracing (fallback)
```

### The 8-Step Workflow

| Step | What the Agent Does |
|------|---------------------|
| 1 | Identifies changed files (git / explicit list) |
| 2 | Asks for output location |
| 3 | Runs the Python analysis engine |
| 4 | Reads the generated JSON data |
| 5 | Provides AI analysis (Impact Summary, Blast Radius, Contract Assessment, Release Recommendation) |
| 6 | Outputs the full AI analysis in chat |
| 7 | Writes AI content back into the report file |
| 8 | Reports completion with a summary table |

### Manual Fallback

If the Python engine is unavailable, the skill falls back to a pure-agent
mode: it uses `grep_search` to manually trace imports up to 3 hops, locates
ownership files with `file_search`, and manually applies the risk scoring
table to produce the report.

---

## 4. Script: change_impact_skill.py — Orchestrator

**File:** `scripts/change_impact_skill.py`

The CLI entry point.  Coordinates the five analysis engines in sequence and
writes the output files.

### Interface

```
usage: change_impact_skill.py [options]

options:
  --repo-path PATH      Root of the repository (default: current directory)
  --changed-files FILE  One or more explicit file paths
  --from-git            Auto-detect from git diff HEAD...<base>
  --base-branch BRANCH  Base branch for git diff (default: main)
  --output DIR          Output directory (default: <repo>/change-impact-output/)
  --format FORMAT       markdown | json | both (default: both)
  --json-only           Emit JSON to stdout only; no files written
```

### Execution Sequence

```
1  Resolve changed files  (git diff or explicit list)
2  DependencyGraphBuilder.build()      →  DependencyGraph
3  OwnershipParser.parse()             →  OwnershipMap
4  ContractValidator.validate()        →  [violations]
5  ImpactAnalyzer.analyze(files)       →  impact dict
6  RiskScorer.score(impact, violations) →  risk dict
7  ReportGenerator.generate_*()       →  output files
```

### Output Structures

**Risk dict:**
```json
{
  "score": 42,
  "level": "MEDIUM",
  "action": "Deploy with monitoring. Notify on-call team.",
  "factors": [
    {"factor": "change_volume",   "points": 8,  "detail": "7 files changed"},
    {"factor": "transitive_spread","points": 14, "detail": "22 modules transitively affected"},
    ...
  ]
}
```

**Impact dict:**
```json
{
  "changed_files":          ["src/api/users.py", ...],
  "impacted_modules":       [{"path": "...", "module_type": "api_endpoint", "change_proximity": "direct", "owners": ["@team"], "risk_factors": [...]}],
  "impacted_apis":          [{"path": "...", "owners": [...], "proximity": "direct"}],
  "regression_areas":       ["[api_endpoint] src/api/users.py", ...],
  "required_test_suites":   ["integration/src/api", "unit/src/services"],
  "consumer_apps":          ["orders-service", "billing-service"],
  "direct_impact_count":    3,
  "transitive_impact_count": 22
}
```

---

## 5. Engine: graph_builder.py — Dependency Graph

**File:** `scripts/engine/graph_builder.py`

### Data Structure

```
DependencyGraph
├── nodes: Set[str]                     # All source file paths (repo-relative)
├── edges: Dict[str, Set[str]]          # A → {B, C}  ("A imports B and C")
├── reverse_edges: Dict[str, Set[str]]  # B → {A}     ("B is imported by A")
└── language_map: Dict[str, str]        # path → language
```

### Build Algorithm

```
1  Walk all source files (respecting IGNORE_DIRS)
2  For each file:
   a  Determine language from extension
   b  Parse import statements (language-specific extractor)
   c  Resolve each import to a repository-relative path
   d  Add edge: file → resolved_import
3  Return completed DependencyGraph
```

### Import Resolution

| Language | Extractor | Resolution |
|----------|-----------|------------|
| Python | `ast.Import` + `ast.ImportFrom` | Tries `module.py` and `module/__init__.py` |
| JS/TS | Regex (`import ... from './path'`, `require('./path')`) | Tries `.js`, `.ts`, `.jsx`, `.tsx`, `/index.js` |
| Java | Regex `import com.example.Class;` | Maps package → `src/.../Class.java` |
| C# | Regex `using MyApp.Services;` | Maps namespace → `Services.cs`, `ServicesController.cs`, etc. |
| Go | Regex `"module/package"` | Maps to `package/package.go` |

**Python fallback:** If `ast.parse()` fails (syntax error, version mismatch),
the extractor falls back to regex matching `^import X` and `^from X import`.

### Reverse BFS (get_reverse_deps)

```python
def get_reverse_deps(node, transitive=True):
    visited = set()
    queue = list(reverse_edges.get(node, []))
    while queue:
        current = queue.pop()
        if current not in visited:
            visited.add(current)
            if transitive:
                queue.extend(reverse_edges.get(current, []))
    return visited
```

**Complexity:** O(V + E) — linear in the size of the subgraph reachable from
the changed file.

**Cycle safety:** The `visited` set prevents infinite loops on circular imports.

---

## 6. Engine: impact_analyzer.py — Blast Radius

**File:** `scripts/engine/impact_analyzer.py`

### Module Classification

Each affected file is classified into one of seven types:

| Type | Detection Method |
|------|-----------------|
| `test` | Path pattern: `test/`, `__tests__/`, `*.spec.*`, `test_*.py` |
| `database` | Path: `migration`, `*.sql`, `models/`, `entities/`, `repository/` |
| `config` | Path: `config.*`, `settings.*`, `Dockerfile`, `docker-compose`, `k8s/` |
| `ui_component` | Extension: `.jsx`, `.tsx`, `.vue`, `.svelte` or path `components/`, `pages/` |
| `api_endpoint` | Content: Spring `@GetMapping`, Flask `@app.get`, Express `router.get`, ASP.NET `[HttpGet]`, Go `http.ResponseWriter` |
| `service` | Path contains `service`, `usecase`, `interactor`, `business` |
| `library` | Path contains `util`, `helper`, `common`, `shared`, `lib` |

### Risk Factors per Module

| Factor | Condition |
|--------|-----------|
| `public_api_surface` | `module_type == api_endpoint` |
| `data_schema_change` | `module_type == database` |
| `configuration_change` | `module_type == config` |
| `shared_dependency` | `module_type == library` |
| `security_sensitive` | Path contains `auth`, `security`, `jwt`, `oauth`, `permission` |
| `financial_critical` | Path contains `payment`, `billing`, `invoice`, `transaction` |
| `external_integration` | Path contains `notification`, `email`, `sms`, `webhook` |

### Output Collection

For each affected module, the analyzer populates:

| Output field | Logic |
|-------------|-------|
| `impacted_apis` | All `api_endpoint` modules |
| `regression_areas` | All `api_endpoint`, `service`, `database` modules |
| `required_test_suites` | `integration/` for APIs, `unit/` for services, `e2e/` for UI |
| `consumer_apps` | Top-level directory names (proxy for service boundaries) |

---

## 7. Engine: risk_scorer.py — Risk Scoring

**File:** `scripts/engine/risk_scorer.py`

The risk model is a **transparent linear sum** of six independent factors,
each with a fixed maximum.  See [`references/risk-scoring.md`](references/risk-scoring.md)
for the complete breakdown with examples.

```
Score = factor_1 + factor_2 + factor_3 + factor_4 + factor_5 + factor_6
      ≤ 100  (capped)

factor_1: change_volume       0..20
factor_2: transitive_spread   0..20
factor_3: breaking_api_changes 0..25
factor_4: module_type_risk    0..20  (db=10, api=6, config=4)
factor_5: sensitivity         0..10  (security=5, financial=5)
factor_6: consumer_breadth    0..5
```

### Risk Levels

| Level | Range | Action |
|-------|-------|--------|
| LOW | 0–30 | Standard release pipeline |
| MEDIUM | 31–60 | Deploy with monitoring; notify on-call |
| HIGH | 61–80 | Senior review + rollback plan |
| CRITICAL | 81–100 | Block; tech lead escalation |

---

## 8. Engine: contract_validator.py — API Contracts

**File:** `scripts/engine/contract_validator.py`

### Supported Contract Types

| Type | Files Detected | Checks |
|------|---------------|--------|
| OpenAPI / Swagger | `openapi.json/yaml`, `swagger.json/yaml`, any JSON/YAML with `openapi:` key | Deprecated endpoints, major version bump, missing required parameter schema |
| GraphQL | `*.graphql`, `*.gql` | `@deprecated` fields, new non-null fields |
| Protobuf | `*.proto` | Missing `reserved` declarations, `[deprecated=true]` fields |

### Discovery Strategy

1. Check fixed filenames: `openapi.json`, `swagger.yaml`, etc.
2. Glob `**/*.yaml`, `**/*.json` and peek first 400 bytes for `openapi:` or `swagger:` key
3. Glob `**/*.graphql`, `**/*.gql`
4. Glob `**/*.proto`

### Violation Severity Levels

| Severity | Meaning |
|----------|---------|
| `breaking` | Clients will fail if not updated (removed endpoint, changed required type) |
| `warning` | Deprecated field/endpoint — migration needed before removal |
| `info` | Non-null field added — may be breaking for existing partial-update clients |

**Note:** The current implementation detects *static* violations in the current
spec file.  A git-diff-based validator (comparing current spec against the base
branch version) is a natural next step for detecting removals/renames.

---

## 9. Engine: ownership_parser.py — Code Ownership

**File:** `scripts/engine/ownership_parser.py`

### Ownership Sources (in priority order)

1. `.github/CODEOWNERS` — highest specificity, supports glob patterns
2. `CODEOWNERS` — root-level fallback
3. `docs/CODEOWNERS` — documentation-level fallback
4. `package.json` `"maintainers"` / `"author"` — covers the entire repo
5. `pyproject.toml` `[tool.poetry] authors` — Python project fallback

### CODEOWNERS Semantics

Follows GitHub's exact semantics: the **last matching rule wins**.

```python
def get_owners(file_path):
    matched = []
    for pattern, owners in rules:      # rules in file order
        if matches(pattern, file_path):
            matched = owners           # later match overwrites earlier
    return matched
```

Pattern matching supports:
- Exact paths: `src/api/users.py`
- Directory wildcards: `src/api/`
- Glob patterns: `*.py`, `docs/**`
- Basename matching: `Makefile` matches anywhere

---

## 10. Engine: report_generator.py — Output Generation

**File:** `scripts/engine/report_generator.py`

Produces three output files from the aggregated result dictionary:

### impact_report.md

Full structured Markdown report with sections:
- Executive Summary (table)
- Deployment Risk Score + factor breakdown table
- Changed Files list
- Impacted API Endpoints table (path, owners, proximity)
- Impacted Modules table (path, type, proximity, owners, risk factors)
- Potential Regression Areas
- Required Test Suites (checkbox list)
- Consumer Applications Affected
- API Contract Violations table

### impact_analysis.json

Complete machine-readable result.  Suitable for:
- CI/CD pipeline gates (check `risk.score > 80`)
- Dashboards and DORA metrics
- Integration with Jira, Linear, PagerDuty
- Historical trend analysis

### deployment_checklist.md

Risk-adaptive checklist:
- **Always included:** pre-deploy sign-off, test execution, owner notifications, post-deploy verification
- **HIGH risk:** senior engineer sign-off, performance test
- **CRITICAL risk:** tech lead approval, incident response on standby, canary strategy, feature flag

---

## 11. Templates

### templates/impact_report.md

Markdown template with `{{PLACEHOLDER}}` tokens.  Used as the structural
skeleton — the Python generator fills these programmatically.  The agent
can also use this template in manual-fallback mode.

### templates/deployment_checklist.md

Checklist template with `{{#HIGH_RISK}}...{{/HIGH_RISK}}` conditional blocks
that expand based on the risk level.  The Python generator handles expansion;
in manual mode the agent applies the conditionals based on the score.

---

## 12. End-to-End Data Flow

```
User: "Analyse the change impact for my branch"
  │
  ▼
SKILL.md triggers (description field matches)
  │
  ▼
Step 1: Identify changed files
  git diff --name-only main...HEAD  →  [src/api/users.py, src/models/user.py]
  │
  ▼
Step 3: Run engine
  change_impact_skill.py --from-git
  │
  ├─▶ graph_builder.build()
  │     Walk all .py/.js/.ts/... files
  │     Parse imports with AST / regex
  │     Build adjacency list + reverse adjacency list
  │     Returns: DependencyGraph(nodes=1420, edges=3840)
  │
  ├─▶ ownership_parser.parse()
  │     Read .github/CODEOWNERS
  │     Build OwnershipMap(rules=24)
  │
  ├─▶ contract_validator.validate()
  │     Find openapi.yaml → parse → check deprecated endpoints
  │     Returns: [violation: deprecated POST /users/{id}]
  │
  ├─▶ impact_analyzer.analyze([src/api/users.py, src/models/user.py])
  │     Normalise paths
  │     Reverse BFS from each changed file
  │     Classify each affected module by type
  │     Assign risk factors per module
  │     Returns: impact{direct=2, transitive=14, apis=3, consumers=["orders"]}
  │
  ├─▶ risk_scorer.score(impact, violations)
  │     change_volume(2 files)      =  4 pts
  │     transitive_spread(14)       =  8 pts
  │     breaking_api_changes(0)     =  0 pts  (only deprecation warning)
  │     module_type(api+service)    =  6 pts
  │     sensitivity(none)           =  0 pts
  │     consumer_breadth(1)         =  1 pt
  │     ─────────────────────────────────────
  │     Total: 19/100 → LOW
  │
  └─▶ report_generator.generate_markdown/json/checklist()
        Write impact_report.md
        Write impact_analysis.json
        Write deployment_checklist.md
  │
  ▼
Step 4: Copilot reads impact_analysis.json
Step 5: Copilot generates AI narrative
  - Impact Summary
  - Blast Radius Explanation
  - API Contract Assessment
  - Release Recommendation: PROCEED
Step 7: Appends AI content to impact_report.md
Step 8: Prints completion summary
```

---

## 13. Configuration & Extension

### Adding a New Language

1. Add the extension → language mapping in `graph_builder.py`:
   ```python
   LANGUAGE_MAP = {
       ".rb": "ruby",    # new
       ...
   }
   ```
2. Implement `_ruby_imports(self, content, file_path)` using a regex pattern
   for `require` / `require_relative`.
3. Add a resolver method if relative paths need normalisation.

### Adding a New Risk Factor

In `risk_scorer.py`, add a new block in the `score()` method:
```python
# Factor 7: Test coverage gap (max 10 pts)
coverage = context.get("coverage_percent", 100)
pts = max(0, int((100 - coverage) / 10))
total += pts
factors.append({"factor": "test_coverage_gap", "points": pts, "detail": f"{coverage}% coverage"})
```

### Adding a New Contract Type (e.g., AsyncAPI)

In `contract_validator.py`:
1. Add a new `_find_asyncapi_specs()` discovery method
2. Implement `_validate_asyncapi(spec_path)` 
3. Call it from `validate()`

### Integrating with Git Diff (Breaking-Change Detection)

Replace the current static analysis with a diff-based approach:
```python
# In contract_validator.py
old_spec = subprocess.run(
    ["git", "show", f"{self.base_branch}:openapi.yaml"],
    capture_output=True, text=True
).stdout
current_spec = spec_path.read_text()
# Compare old_spec vs current_spec for removed endpoints, changed types
```

---

## 14. CI/CD Integration

### GitHub Actions — Risk Gate

```yaml
name: Change Impact Gate
on: [pull_request]

jobs:
  impact-analysis:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install optional dependencies
        run: pip install PyYAML

      - name: Run Change Impact Analysis
        id: impact
        run: |
          python .github/skills/change-impact-analysis/scripts/change_impact_skill.py \
            --from-git --base-branch ${{ github.base_ref }} \
            --output ./impact-output
          
          SCORE=$(python -c "import json; d=json.load(open('impact-output/impact_analysis.json')); print(d['risk']['score'])")
          LEVEL=$(python -c "import json; d=json.load(open('impact-output/impact_analysis.json')); print(d['risk']['level'])")
          echo "score=$SCORE" >> $GITHUB_OUTPUT
          echo "level=$LEVEL" >> $GITHUB_OUTPUT

      - name: Upload Impact Report
        uses: actions/upload-artifact@v4
        with:
          name: impact-report
          path: ./impact-output/

      - name: Fail on Critical Risk
        if: steps.impact.outputs.score > 80
        run: |
          echo "::error::Deployment risk CRITICAL (${{ steps.impact.outputs.score }}/100)"
          echo "::error::Human review required before merging."
          exit 1
```

### JSON Output Fields for CI

```bash
# Check risk level
python change_impact_skill.py --from-git --json-only \
  | python -c "import sys,json; r=json.load(sys.stdin); print(r['risk']['level'])"

# Count impacted APIs
python change_impact_skill.py --from-git --json-only \
  | python -c "import sys,json; r=json.load(sys.stdin); print(len(r['impact']['impacted_apis']))"

# List all consumer apps
python change_impact_skill.py --from-git --json-only \
  | python -c "import sys,json; r=json.load(sys.stdin); print('\n'.join(r['impact']['consumer_apps']))"

# List owners to notify
python change_impact_skill.py --from-git --json-only \
  | python -c "
import sys, json
r = json.load(sys.stdin)
owners = {o for m in r['impact']['impacted_modules'] for o in (m.get('owners') or [])}
print('\n'.join(sorted(owners)))
"
```
