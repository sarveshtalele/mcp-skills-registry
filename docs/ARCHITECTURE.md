# Architecture

The registry is a small FastAPI service with a clean, layered design. Each layer
depends only on the layers beneath it, which keeps the code testable and easy to
extend.

```
api/        HTTP routers (health, mcp, rest)        ← transport
  │
mcp/        JSON-RPC 2.0 protocol handler           ← MCP wire format
  │
services/   registry, loader, validator, executor,  ← application logic
            search, audit
  │
repositories/  execution + audit persistence        ← data access
  │
db/         SQLite wrapper + schema.sql              ← storage
  │
models/     pydantic domain models                   ← shared types
config.py   env-driven settings
container.py composition root (build_container)
```

## Key components

| Component | Responsibility |
|-----------|----------------|
| `SkillLoader` | Discover `skills/*/SKILL.md`, parse frontmatter into a validated `SkillManifest`. |
| `InputValidator` | Validate caller inputs against the manifest (types, required, enums, defaults). |
| `SkillExecutor` | Run a skill in an isolated subprocess (`_runner.py`) with a hard timeout. |
| `SearchService` | Rank skills by keyword (default) or semantic similarity (opt-in). |
| `SkillInstaller` | Install an uploaded ZIP skill safely (zip-slip / zip-bomb guards). |
| `AuditService` | Append-only audit trail; never breaks the request path. |
| `SkillRegistry` | Facade that coordinates all of the above and records executions. |
| `MCPHandler` | Translate JSON-RPC `initialize` / `tools/list` / `tools/call` to registry calls. |
| `SessionManager` | Track Streamable-HTTP MCP sessions (`Mcp-Session-Id`). |

## Execution model

`python-script` skills run **out-of-process**:

1. The executor spawns `python _runner.py <entrypoint.py> <callable>`.
2. Validated inputs are sent as JSON on stdin.
3. The runner imports the entrypoint, calls `run(inputs)`, and prints a JSON
   envelope (`{"output": ...}` or `{"error": ...}`) on stdout.
4. The parent enforces the timeout (killing the child on overrun) and an
   output-size cap.

This gives process isolation, a clean import namespace per call, and reliable
timeouts without threads.

## Data

Skills themselves live on disk under `skills/` — they are the source of truth and
are versioned in Git. SQLite (`data/registry.db`) holds only **runtime** data:
execution history and the audit log. On Hugging Face Spaces this lives on the
persistent `/data` mount.

## Design gaps addressed vs. the original prototype

| Gap | Resolution |
|-----|-----------|
| Monolithic `app.py` | Split into a layered package under `src/`. |
| Invalid SQLite (`INDEX` inline) | Separate `CREATE INDEX` statements in `schema.sql`. |
| Fake `exec()` sandbox | Real subprocess isolation + timeout + output cap. |
| `asdict()` on pydantic models | Proper pydantic v2 serialization throughout. |
| No input validation | `InputValidator` enforces the manifest schema. |
| No tests / linting | pytest suite + ruff + black + mypy + CI. |
| Skills coupled to server code | Self-contained skill folders, auto-discovered. |
