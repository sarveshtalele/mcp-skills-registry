# Reverse Engineering Skill — Engine Architecture Reference

This document describes how the static analysis engine works. GitHub Copilot reads this
to understand what the Python scripts produce and how to interpret the output files.

---

## Pipeline Overview

```
reverse_engineer_skill.py  (CLI entry point)
        ↓
engine/pipeline.py  run_pipeline(repo_url, mode, output_dir)
        ↓
  [1] clone_repo()           — git clone --depth=1
  [2] load_repo()            — loaders.py  — walks source tree
  [3] parse_file()           — parsers.py  — per-language AST extraction
  [4] generate_report()      — analyzer.py — codebase metrics
  [5] extract_api_endpoints()— analyzer.py — route detection
  [6] detect_auth_patterns() — analyzer.py — RBAC/ABAC/ReBAC
  [7] detect_screens_nav()   — analyzer.py — UI screen inventory
  [8] ai_*() functions       — ai_analysis.py — heuristic domain analysis
  [9] generate_sdd()         — generators/sdd.py
      generate_html_dashboard()  — generators/dashboard.py
      generate_md_report()   — generators/report.py
 [10] OutputManager          — output_manager.py — writes files
 [11] evaluate_pipeline_output — evaluator.py — quality score
```

---

## Supported Languages

| Extension | Language | Parser function |
|-----------|----------|----------------|
| `.py` | Python | `parse_python()` |
| `.java` | Java | `parse_java()` |
| `.cs`, `.aspx.cs` | C# / .NET | `parse_dotnet()` |
| `.ts`, `.tsx` | TypeScript | `parse_js_ts()` |
| `.js`, `.jsx` | JavaScript | `parse_js_ts()` |
| `.vb` | VB.NET | `parse_dotnet()` |

---

## Parsed File Record Schema

Each file through the pipeline produces a dict:

```json
{
  "file": "/abs/path/to/File.cs",
  "language": "dotnet",
  "content": "raw source text",
  "classes": ["OrderController", "CartService"],
  "methods": ["GetOrder", "AddItem"],
  "imports": ["Microsoft.AspNetCore", "System.Linq"],
  "dependencies": ["Microsoft.AspNetCore", "System.Linq"],
  "routes": [
    {"path": "/orders/{id}", "methods": ["GET"], "class": "OrderController", "method": "GetOrder"}
  ],
  "db_entities": [
    {"name": "Order", "table": "Orders", "fields": ["Id", "UserId"], "relationships": []}
  ]
}
```

---

## Auth Detection — What Each Model Looks Like

### RBAC (Role-Based Access Control)
Code grants access based on a **named role** assigned to the user.

| Language | Pattern | Example |
|----------|---------|---------|
| C# / ASP.NET | `[Authorize(Roles="Admin")]` | `[Authorize(Roles="Admin,Manager")]` |
| C# / ASP.NET | `User.IsInRole("Manager")` | if check in controller |
| C# / ASP.NET | `ClaimTypes.Role` | claim inspection |
| Java / Spring | `@PreAuthorize("hasRole('ADMIN')")` | method annotation |
| Java / Spring | `@Secured({"ROLE_ADMIN"})` | class or method |
| Python / Flask | `@login_required` | route decorator |
| Python / Flask | `@role_required("admin")` | Flask-Principal |
| Python / Django | `@permission_required(...)` | view decorator |
| JS / TS | `user.roles.includes("admin")` | runtime check |

### ABAC (Attribute/Policy-Based Access Control)
Code grants access based on **attributes, claims, or policies** evaluated at runtime.

| Language | Pattern | Example |
|----------|---------|---------|
| C# / ASP.NET | `[Authorize(Policy="CanEditOrder")]` | named policy |
| C# / ASP.NET | `IAuthorizationRequirement` | custom requirement |
| C# / ASP.NET | `services.AddAuthorization(...)` | policy registration |
| C# / ASP.NET | `RequireAssertion(ctx => ...)` | lambda policy |
| Java / Spring | `@PreAuthorize("hasPermission(...)")` | ABAC expression |
| Java / Spring | `@PostAuthorize` | post-method check |
| Python / Django | `ObjectPermission` | per-object permission |

### ReBAC (Relationship-Based Access Control)
Code grants access based on the **relationship** between the user and the resource.

| Language | Pattern | Meaning |
|----------|---------|---------|
| Any | `IsOwner(resource, user)` | user created/owns this resource |
| C# | `order.UserId == currentUserId` | owner comparison |
| C# | `HasPermissionOnResource(user, res)` | explicit relationship check |
| Any | `CreatedBy == User.Id` | created-by ownership |
| Any | `resource.OwnedBy(user)` | relationship method |

---

## Output Files Reference

| File | Contents | Primary Consumer |
|------|---------|-----------------|
| `{repo}_report.md` | 4-section focused report (System Design, Auth, Business Logic, Screens) | Human stakeholders, Copilot AI narrative |
| `{repo}_sdd.json` | Full JSON SDD — 16 sections including `auth_analysis`, `screens_navigation` | AI assistants, tooling |
| `{repo}_dashboard.html` | Self-contained HTML — no server, share by email | Non-technical stakeholders |
| `{repo}_block_diagram.svg` | Architecture layers SVG | Presentations, docs |
| `{repo}_dependency_graph.svg` | Module dependency graph SVG | Code review, refactoring |
| `{repo}_evaluation.md` | 100-point quality score with confidence band | QA, architects |
| `manifest.json` | Run metrics: files, classes, endpoints, timestamps | CI, tooling |

---

## SDD JSON — Key Sections for AI Navigation

When Copilot reads `{repo}_sdd.json`, here are the paths to key data:

```
sdd.project.language           — primary language ("dotnet", "java", "python", ...)
sdd.project.tech_stack         — ["ASP.NET Core", "Entity Framework", ...]
sdd.codebase_metrics           — {total_files, total_classes, total_methods}
sdd.api_catalog.endpoints[]    — {path, methods, class, method, file}
sdd.data_architecture.entities[] — {name, table, fields[], relationships[]}
sdd.business_logic.business_domain
sdd.business_logic.core_workflows[]
sdd.business_logic.user_roles[]
sdd.business_logic.key_business_rules[]
sdd.auth_analysis.auth_type    — "RBAC (Role-Based)" | "Hybrid RBAC+ABAC" | ...
sdd.auth_analysis.rbac[]       — [{file, pattern, example}]
sdd.auth_analysis.abac[]       — [{file, pattern, example}]
sdd.auth_analysis.rebac[]      — [{file, pattern, example}]
sdd.auth_analysis.roles_detected[]
sdd.auth_analysis.policies_detected[]
sdd.auth_analysis.protected_routes[]
sdd.auth_analysis.public_routes[]
sdd.screens_navigation.project_type
sdd.screens_navigation.screens[] — {name, file, type, routes[], description}
sdd.screens_navigation.navigation_flow[] — {from, to, label}
sdd.modernization_roadmap.phases[]
sdd.modernization_roadmap.estimated_total_effort
```

---

## File Cap & Prioritisation

For large repos (>300 files) the engine samples intelligently:

| Layer | Slots | Rationale |
|-------|-------|-----------|
| Controllers / Handlers | 75 | Entry points — API surface |
| Services / Managers | 75 | Business logic |
| Repositories / DAOs | 40 | Data access |
| Domain / Entities | 60 | Database schema |
| Models / DTOs | 30 | Data shapes |
| Everything else | 20 | Infrastructure |

---

## How the Script Resolves Paths

`scripts/reverse_engineer_skill.py` adds its own directory to `sys.path` at startup:

```python
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPT_DIR)
```

This means you can invoke it from any working directory as:
```bash
python .github/skills/reverse-engineering-skill/scripts/reverse_engineer_skill.py <url>
```
