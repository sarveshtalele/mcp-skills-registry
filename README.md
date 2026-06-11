<div align="center">

# 🧩 MCP Skill Registry

### A self-hostable [Model Context Protocol](https://modelcontextprotocol.io) server that turns a folder of "skills" into tools any MCP client can discover and run.

[![CI](https://github.com/sarveshtalele/mcp-skills-registry/actions/workflows/ci.yml/badge.svg)](https://github.com/sarveshtalele/mcp-skills-registry/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Hugging Face Space](https://img.shields.io/badge/%F0%9F%A4%97%20Live%20Demo-Hugging%20Face-orange)](https://sarveshtalele-mcp-skills-registry.hf.space)

[What It Does](#-what-it-does) · [Quick Start](#-quick-start) · [Built-in Skills](#-built-in-skills) · [Connect a Client](#-connect-an-mcp-client) · [Author a Skill](#-authoring-a-skill) · [Deploy](#-deployment) · [Contributing](#-contributing)

</div>

---

## 🎯 What It Does

**MCP Skill Registry** is one server that hosts many *skills* and exposes each one as a callable tool.

A **skill** is just a folder containing a `SKILL.md` manifest and a small script. Drop the folder in, and the server:

1. **Discovers** it automatically (reads the manifest at startup).
2. **Publishes** it on two interfaces at once:
   - as an **MCP tool** — usable from Claude Code, Claude Desktop, VS Code, Cursor, or any MCP client;
   - as a **REST endpoint** — usable from `curl`, scripts, or any HTTP app.
3. **Executes** it safely in an isolated subprocess with a hard timeout.

You add capabilities by **adding folders or uploading a ZIP — never by editing the server**.

```text
   ┌─────────────┐     "list/run tools"      ┌────────────────────┐
   │  MCP client │ ────────────────────────► │                    │
   │ Claude Code │                           │   MCP Skill        │
   │ Claude Dsk. │ ◄──────────────────────── │   Registry server  │
   │  VS Code    │      tool results         │                    │
   └─────────────┘                           │   discovers every  │
   ┌─────────────┐     POST /api/v1/...      │   skills/<name>/   │
   │ REST caller │ ◄────────────────────────►│   folder           │
   └─────────────┘                           └─────────┬──────────┘
                                                       │ runs in
                                                       ▼ subprocess
                                          skills/text-statistics/
                                          skills/your-skill/ ...
```

---

## ✨ Features

| | Feature | Description |
|---|---|---|
| 🔌 | **Dual interface** | Every skill is an MCP tool *and* a REST resource |
| 🧭 | **Zero-config discovery** | Skills are plain folders; no registration code |
| 🛡️ | **Sandboxed execution** | Subprocess isolation, per-skill timeouts, output caps |
| 📤 | **Live uploads** | Install a skill from a ZIP via the API or dashboard; no restart |
| 🌐 | **Native MCP** | Streamable HTTP transport with sessions; no bridge needed |
| 🔍 | **Search** | Keyword out of the box, optional semantic (vector) search |
| 🏭 | **Engineering Factory** | Built-in skill suite for legacy modernization and governance |
| 📐 | **Spec-Driven Development** | SpecKit skills drive a project from idea to backlog |
| 🤖 | **Agent orchestration** | Agents compose skills into multi-step workflows |
| 🖥️ | **Dashboard UI** | Apple-inspired Next.js dashboard for browsing, searching, and uploading |
| 📝 | **Audit trail** | Append-only event log for every execution and catalogue change |
| 🧱 | **Clean codebase** | Layered, typed, 37+ tests, CI on Python 3.10–3.12 |

---

## 🚀 Quick Start

### Local development

```bash
git clone https://github.com/sarveshtalele/mcp-skills-registry.git
cd mcp-skills-registry

python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

skill-registry          # serves on http://localhost:7860
```

```bash
curl http://localhost:7860/health
# {"status":"ok","version":"0.2.0","skills_loaded":1}
```

### Docker

```bash
docker build -t mcp-skill-registry .
docker run -p 7860:7860 -v "$(pwd)/data:/data" mcp-skill-registry
```

### Live demo

A public instance runs at **https://sarveshtalele-mcp-skills-registry.hf.space** — try the dashboard, browse skills, or connect your MCP client directly.

---

## 🏗️ Built-in Skills

The registry ships with production-ready skill suites out of the box.

### 📐 SpecKit — Spec-Driven Development

Inspired by [GitHub Spec Kit](https://github.com/github/spec-kit), these skills drive a project from idea to backlog — usable from any MCP client:

| Skill | Produces |
|---|---|
| `speckit-constitution` | Project principles (`constitution.md`) |
| `speckit-specify` | A structured spec (`spec.md`) from a feature description |
| `speckit-plan` | A technical plan (`plan.md`) from a spec summary |
| `speckit-tasks` | An ordered task backlog (`tasks.md`) from a plan |

**Flow:** `constitution → specify → plan → tasks`, committing each artifact as you go.

### 🏭 Factory — Governed Engineering

A modernization suite that takes a legacy system from discovery to a governed release:

| Skill | Purpose |
|---|---|
| `legacy-discovery` | Reverse-engineer a legacy app (scans a repo URL or local path) → spec + architecture + inventory |
| `topology-planning` | Target architecture + phased migration plan + ADRs |
| `task-decomposition` | Spec → dependency-ordered `tasks.yaml` backlog |
| `ui-modernization` | Legacy UI → React component plan + starter stubs |
| `test-generation` | Unit/integration/e2e test strategy + stubs |
| `spec-governance` | Compliance audit with a pass/fail gate and score |

**Flow:** `legacy-discovery → topology-planning → task-decomposition → ui-modernization → test-generation → spec-governance`

### 🔍 Change Impact Analysis

A graph-driven change impact analysis skill that builds dependency graphs, finds directly and transitively affected modules, validates API contracts for breaking changes, parses `CODEOWNERS`, and computes a 0–100 deployment risk score.

### 📊 Text Statistics

A simple, worked example skill — computes word count, character count, sentence count, and reading level for any text.

---

## 🔬 Real-World Example: Reverse-Engineering nopCommerce

The `legacy-discovery` skill can reverse-engineer entire codebases. Here's what it produces when pointed at the [nopCommerce repository](https://github.com/nopSolutions/nopCommerce) — a 3M+ download, enterprise-grade e-commerce platform:

<details>
<summary><strong>📋 Click to expand: nopCommerce analysis output (generated by legacy-discovery)</strong></summary>

The skill automatically produces:

- **System Design Document** — full architectural analysis with layered architecture model
- **150+ domain entity inventory** — Products, Orders, Customers, Payments, Shipping, etc.
- **50+ service module mapping** — `ICatalogService`, `IOrderService`, `IPaymentService`, etc.
- **Plugin architecture breakdown** — Payment, Shipping, Tax, Auth, Widget plugin taxonomies
- **Database schema analysis** — entity relationships, migration history (1.90 → 5.00)
- **Security architecture** — RBAC, AES encryption, GDPR compliance, OWASP headers
- **Event system documentation** — pub/sub patterns, cache invalidation chains
- **100-point quality score** — codebase health metrics

All from a single command:

```bash
# Via MCP client
"Reverse engineer https://github.com/nopSolutions/nopCommerce"

# Via REST API
curl -X POST http://localhost:7860/api/v1/skills/legacy-discovery/execute \
  -H 'Content-Type: application/json' \
  -d '{"inputs": {"repo_url": "https://github.com/nopSolutions/nopCommerce"}}'
```

The returned analysis includes architectural diagrams, code patterns, entity relationships, and actionable modernization recommendations — no manual effort required.

</details>

---

## 🤖 Agents

Agents orchestrate skills through multi-step workflows. Load one in your MCP client to drive an end-to-end process:

| Agent | Orchestrates | Purpose |
|---|---|---|
| `arch-analyst` | `legacy-discovery` → `topology-planning` | Reverse-engineer & define target architecture |
| `migration-eng` | `task-decomposition` → `ui-modernization` → `test-generation` | Build the modernization solution |
| `gatekeeper` | `spec-governance` | Governance & compliance enforcement |

`GET /api/v1/agents` lists them; upload your own via the dashboard or `POST /api/v1/agents/upload`.

---

## 🖥️ Dashboard UI

An Apple-inspired **Next.js** dashboard is the landing page (static export built into the image; served by FastAPI). It lets you:

- **Browse** all skills and agents with search
- **Upload** a skill, a speckit skill, or an agent — *Validate format* first, then *Upload & Publish*
- **Delete** skills and agents directly from the UI

With `SKILLREG_GITHUB_TOKEN` set, publishing also commits to the repo's `skills/` or `agents/` folder, redeploying the Space.

**Live:** [sarveshtalele-mcp-skills-registry.hf.space](https://sarveshtalele-mcp-skills-registry.hf.space/)

---

## 🔗 Connect an MCP Client

The server speaks **Streamable HTTP** MCP transport at `/mcp`. Use your local URL (`http://localhost:7860/mcp`) or the hosted one (`https://sarveshtalele-mcp-skills-registry.hf.space/mcp`).

### Claude Code

```bash
claude mcp add --transport http skill-registry \
  https://sarveshtalele-mcp-skills-registry.hf.space/mcp
```

Verify inside a session:

```text
/mcp          # lists connected servers and their tools
```

Remove with `claude mcp remove skill-registry`.

### Claude Desktop

1. Open **Settings → Developer → Edit Config** (opens `claude_desktop_config.json`).
2. Add the server:

   ```json
   {
     "mcpServers": {
       "skill-registry": {
         "command": "npx",
         "args": [
           "-y", "mcp-remote",
           "https://sarveshtalele-mcp-skills-registry.hf.space/mcp"
         ]
       }
     }
   }
   ```

   > Claude Desktop launches MCP servers as local processes, so it reaches a remote
   > HTTP server through the `mcp-remote` bridge (`npx` fetches it automatically;
   > requires Node.js). Alternatively, **Settings → Connectors → Add custom connector**
   > accepts the `/mcp` URL directly on supported plans.

3. Restart Claude Desktop. The skills appear as tools (look for the 🔌 icon).

### VS Code (GitHub Copilot / Continue)

Create `.vscode/mcp.json`:

```json
{
  "servers": {
    "skill-registry": {
      "type": "http",
      "url": "https://sarveshtalele-mcp-skills-registry.hf.space/mcp"
    }
  }
}
```

### Any MCP client (raw protocol)

The endpoint is JSON-RPC 2.0 over HTTP POST.

```bash
# 1. initialize — returns an Mcp-Session-Id header
curl -i -X POST http://localhost:7860/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'

# 2. list tools
curl -X POST http://localhost:7860/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'

# 3. call a tool
curl -X POST http://localhost:7860/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call",
       "params":{"name":"text-statistics","arguments":{"text":"Hello world."}}}'
```

| Method | Behaviour |
|---|---|
| `POST /mcp` | `initialize`, `tools/list`, `tools/call`, `ping` (single or batch) |
| `GET /mcp` | `405` — no server-initiated stream (spec-permitted) |
| `DELETE /mcp` | Terminate the session in the `Mcp-Session-Id` header |

---

## 🧰 REST API

Every skill is reachable without MCP. Interactive Swagger UI is served at `/docs`.

| Method & Path | Description |
|---|---|
| `GET /` | Service metadata + entry points |
| `GET /health` | Liveness probe + skill count |
| `GET /api/v1/skills` | List / search skills (`q`, `category`, `limit`, `offset`) |
| `GET /api/v1/skills/{name}` | Full skill manifest |
| `POST /api/v1/skills/{name}/execute` | Run a skill — body `{"inputs": {...}}` |
| `POST /api/v1/skills/upload` | Install a skill from a ZIP (`?overwrite=true`) |
| `POST /api/v1/skills/validate` | Validate a skill ZIP without installing |
| `DELETE /api/v1/skills/{name}` | Delete a skill |
| `GET /api/v1/agents` | List all agents |
| `POST /api/v1/agents/upload` | Install an agent from a ZIP |
| `DELETE /api/v1/agents/{name}` | Delete an agent |
| `POST /api/v1/admin/reload` | Re-scan the skills and agents directories |

```bash
# Example: run a skill
curl -X POST http://localhost:7860/api/v1/skills/text-statistics/execute \
  -H 'Content-Type: application/json' \
  -d '{"inputs": {"text": "The quick brown fox jumps over the lazy dog."}}'
```

---

## ⚙️ Architecture

The server is a small, layered FastAPI application. Each layer depends only on the layers beneath it, keeping it testable and easy to extend.

```text
┌──────────────────────────────────────────────────────────────────────┐
│                     FastAPI application  (port 7860)                │
│                                                                     │
│   api/        Routers:  /  ·  /health  ·  /mcp  ·  /api/v1/skills  │  ← transport
│     │                                                               │
│   mcp/        Streamable HTTP transport · JSON-RPC 2.0 · sessions   │  ← MCP protocol
│     │                                                               │
│   services/   SkillRegistry (facade)                                │  ← application
│     │           ├─ loader      parse & validate SKILL.md            │     logic
│     │           ├─ validator   check inputs against the manifest    │
│     │           ├─ executor    run skill in a sandboxed subprocess  │
│     │           ├─ search      keyword / optional semantic ranking  │
│     │           ├─ installer   safe ZIP upload (zip-slip/bomb guard)│
│     │           ├─ publisher   auto-commit to GitHub on upload      │
│     │           └─ audit       append-only event log                │
│     │                                                               │
│   repositories/  execution history · audit trail                    │  ← persistence
│     │                                                               │
│   db/  models/  config/  container/  main                           │  ← storage, types,
│         SQLite + schema.sql · pydantic models · settings · wiring   │     wiring
└───────────────────────────────────┬──────────────────────────────────┘
                                    │ discovers & executes
                                    ▼
                       skills/   self-contained skill folders
                         └─ <name>/  SKILL.md · scripts/ · references/ · assets/
```

### Request lifecycle (running a tool)

```text
client → tools/call (MCP)  or  POST /api/v1/skills/{name}/execute (REST)
   │
   ├─ 1. look up the skill in the in-memory catalogue        (404 if unknown)
   ├─ 2. validate inputs against SKILL.md                    (types, required, enums)
   ├─ 3. spawn subprocess: python _runner.py <skill> run     (isolated, timed)
   │         inputs → JSON via stdin   ·   output → JSON via stdout
   ├─ 4. enforce timeout + output-size cap                   (kill child on overrun)
   ├─ 5. record execution + audit entry                      (SQLite)
   └─ 6. return { status, output | error, duration_ms }
```

**Why subprocesses?** Process-level isolation, a clean import namespace per call, and a reliable hard timeout — a misbehaving skill can never hang or crash the server.

---

## 🧩 Authoring a Skill

A skill is one self-contained folder:

```text
skill-name/
├── SKILL.md          # Required: YAML frontmatter (manifest) + instructions
├── scripts/          # Optional: code — entrypoint exposes run(inputs) -> dict
├── references/       # Optional: supporting docs
├── assets/           # Optional: templates, resources, extra requirements.txt
└── ...               # Any additional files
```

### 1. Scaffold

```bash
python scripts/new_skill.py my-skill
```

### 2. Define `SKILL.md`

```yaml
---
name: my-skill
version: 1.0.0
description: What it does and the phrases that should trigger it.
execution:
  type: python-script
  entrypoint: scripts/main.py:run
  timeout_seconds: 30
inputs:
  - name: text
    type: string
    required: true
    description: Text to process.
outputs:
  - name: result
    type: string
    description: Processed text.
---

# My Skill
Instructions for the agent.
```

### 3. Implement `scripts/main.py`

```python
def run(inputs: dict) -> dict:
    return {"result": inputs["text"].upper()}
```

### 4. Register

```bash
# Option A: reload the running server
curl -X POST http://localhost:7860/api/v1/admin/reload

# Option B: upload a packaged skill (no restart needed)
zip -r my-skill.zip my-skill/
curl -X POST http://localhost:7860/api/v1/skills/upload -F 'file=@my-skill.zip'
```

📖 Full guide: **[docs/ADDING_A_SKILL.md](docs/ADDING_A_SKILL.md)**

---

## 🌍 Deployment

### Hugging Face Spaces (recommended)

The project is designed for **Hugging Face Docker Spaces** out of the box.

```text
GitHub (source of truth)  ──push main──►  HF Space (Docker build)  ──►  live MCP server
        │                                         │
   CI: lint + test                        Dockerfile → uvicorn :7860
```

1. Create a Docker Space on [huggingface.co/new-space](https://huggingface.co/new-space)
2. Add `HF_TOKEN` secret and `HF_USERNAME`/`HF_SPACE` variables to your GitHub repo
3. Push to `main` — CI runs lint + tests, then auto-deploys to the Space

### Docker (anywhere)

```bash
docker build -t mcp-skill-registry .
docker run -p 7860:7860 -v "$(pwd)/data:/data" mcp-skill-registry
```

### Manual deploy

```bash
pip install huggingface_hub
huggingface-cli login
huggingface-cli upload <user>/mcp-skill-registry . . --repo-type space
```

📖 Full guide: **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**

---

## 🔧 Configuration

All settings are environment variables with the `SKILLREG_` prefix (see [.env.example](.env.example)):

| Variable | Default | Description |
|---|---|---|
| `SKILLREG_HOST` | `0.0.0.0` | Bind address |
| `SKILLREG_PORT` | `7860` | HTTP port |
| `SKILLREG_LOG_LEVEL` | `INFO` | Logging verbosity |
| `SKILLREG_SKILLS_DIR` | `skills` | Skill catalogue directory |
| `SKILLREG_AGENTS_DIR` | `agents` | Agent catalogue directory |
| `SKILLREG_DB_PATH` | `data/registry.db` | SQLite database path |
| `SKILLREG_DEFAULT_TIMEOUT_SECONDS` | `30` | Default execution timeout |
| `SKILLREG_MAX_TIMEOUT_SECONDS` | `120` | Upper bound on any timeout |
| `SKILLREG_MAX_OUTPUT_BYTES` | `1000000` | Max skill output size (1 MB) |
| `SKILLREG_ENABLE_UPLOADS` | `true` | Allow the upload endpoint |
| `SKILLREG_MAX_UPLOAD_BYTES` | `5000000` | Max upload archive size |
| `SKILLREG_ENABLE_SEMANTIC_SEARCH` | `false` | Vector search (needs the `search` extra) |
| `SKILLREG_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformer model for semantic search |
| `SKILLREG_GITHUB_TOKEN` | *(empty)* | GitHub PAT for auto-publish on upload |
| `SKILLREG_GITHUB_REPO` | `sarveshtalele/mcp-skills-registry` | Target repo for auto-publish |
| `SKILLREG_ENABLE_UI` | `true` | Serve the Next.js dashboard at `/` |
| `SKILLREG_FRONTEND_DIR` | `frontend/out` | Path to the Next.js static export |

---

## 🧪 Development

```bash
make install   # editable install with dev extras
make test      # pytest (37+ tests)
make lint      # ruff + black --check
make format    # ruff --fix + black
make run       # local dev server
```

CI runs lint + tests on every push and PR across Python 3.10, 3.11, and 3.12.

### Running tests

```bash
pytest -q                     # all tests
pytest tests/test_api.py      # specific test module
pytest -k "test_upload"       # by name pattern
```

### Code quality

| Tool | Purpose | Config |
|---|---|---|
| [ruff](https://docs.astral.sh/ruff/) | Linting (E/W/F/I/UP/B/N/C4) | `pyproject.toml` |
| [black](https://black.readthedocs.io/) | Formatting (line-length 100) | `pyproject.toml` |
| [mypy](https://mypy-lang.org/) | Type checking | `pyproject.toml` |
| [pytest](https://pytest.org/) | Testing (async mode) | `pyproject.toml` |

---

## 📁 Project Structure

```text
mcp-skills-registry/
├── src/skill_registry/         # the server (layered package)
│   ├── api/                    # HTTP routers (health, mcp, rest)
│   ├── mcp/                    # JSON-RPC 2.0 protocol handler
│   ├── services/               # business logic
│   │   ├── registry.py         # facade: coordinates all services
│   │   ├── loader.py           # SKILL.md parser & skill discovery
│   │   ├── validator.py        # input validation against manifests
│   │   ├── executor.py         # subprocess execution + timeout
│   │   ├── _runner.py          # child process skill runner
│   │   ├── search.py           # keyword & semantic search
│   │   ├── installer.py        # ZIP upload (zip-slip/bomb guards)
│   │   ├── github_publisher.py # auto-commit uploads to GitHub
│   │   ├── agent_loader.py     # AGENT.md parser & agent discovery
│   │   └── audit.py            # append-only audit trail
│   ├── repositories/           # execution history & audit persistence
│   ├── db/                     # SQLite wrapper + schema.sql
│   ├── models/                 # pydantic domain models
│   ├── config.py               # env-driven settings (SKILLREG_*)
│   ├── container.py            # composition root (build_container)
│   └── main.py                 # app factory + CLI entrypoint
│
├── skills/                     # self-contained skills (auto-discovered)
│   ├── _template/              # scaffold skeleton for new skills
│   ├── text-statistics/        # worked example
│   ├── change-impact-analysis/ # graph-driven deployment risk analysis
│   ├── speckit/                # spec-driven development suite
│   │   ├── constitution/
│   │   ├── specify/
│   │   ├── plan/
│   │   └── tasks/
│   └── factory/                # governed engineering suite
│       ├── legacy-discovery/
│       ├── topology-planning/
│       ├── task-decomposition/
│       ├── ui-modernization/
│       ├── test-generation/
│       └── spec-governance/
│
├── agents/                     # agent orchestration definitions
│   ├── arch-analyst/
│   ├── migration-eng/
│   └── gatekeeper/
│
├── frontend/                   # Next.js dashboard (static export)
│   ├── app/                    # Next.js app router pages
│   └── out/                    # built static files (served by FastAPI)
│
├── scripts/                    # utilities
│   ├── new_skill.py            # scaffold a new skill
│   └── hf_entrypoint.sh        # Hugging Face Spaces boot script
│
├── tests/                      # pytest suite
│   ├── test_api.py             # REST API tests
│   ├── test_mcp_transport.py   # MCP protocol tests
│   ├── test_loader.py          # skill loader tests
│   ├── test_validator.py       # input validation tests
│   ├── test_executor.py        # subprocess execution tests
│   ├── test_upload.py          # ZIP upload + install tests
│   ├── test_agents.py          # agent loading + API tests
│   └── test_github_publisher.py # GitHub auto-publish tests
│
├── docs/                       # extended documentation
│   ├── ARCHITECTURE.md         # layered design & execution model
│   ├── ADDING_A_SKILL.md       # full skill authoring guide
│   ├── DEPLOYMENT.md           # GitHub → HF Spaces pipeline
│   └── SKILL_AND_AGENT_REFERENCE.md  # file-by-file reference
│
├── .github/workflows/
│   ├── ci.yml                  # lint + test on Python 3.10–3.12
│   └── deploy-hf.yml          # auto-deploy to Hugging Face Spaces
│
├── Dockerfile                  # multi-stage: Node (frontend) + Python (server)
├── pyproject.toml              # project metadata, deps, tool config
├── requirements.txt            # HF Spaces runtime deps
├── Makefile                    # dev shortcuts (install, test, lint, run)
├── app.py                      # thin ASGI entrypoint shim
├── CONTRIBUTING.md             # contributor guide
└── LICENSE                     # MIT
```

---

## 🗺️ Roadmap

- [ ] **Authentication & API keys** — per-skill access control
- [ ] **Skill versioning** — run multiple versions side-by-side
- [ ] **Execution analytics dashboard** — visualize usage, latency, and error rates
- [ ] **Webhook notifications** — trigger on skill execution events
- [ ] **Plugin marketplace** — community skill discovery and one-click install
- [ ] **Rate limiting** — configurable per-skill and global throttling
- [ ] **Async / streaming execution** — long-running skills with progress updates
- [ ] **Multi-language runtimes** — support Node.js, Go, Rust skill scripts

---

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Dev setup
python -m venv .venv && source .venv/bin/activate
make install

# Before opening a PR
make format         # ruff --fix + black
make lint           # ruff + black --check
make test           # pytest
```

### Adding a skill

Submit a PR that adds a single `skills/<name>/` folder with:
- A valid `SKILL.md` with YAML frontmatter
- An entrypoint exposing `run(inputs) -> dict`
- At least one test

### Conventions

- Layered architecture: `api → services → repositories → db → models` — don't reach across layers
- Type-hint public functions; keep modules small and single-purpose
- Line length 100; formatting by black; linting by ruff

---

## 📖 Documentation

| Document | Description |
|---|---|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Layered design, execution model, data storage |
| [ADDING_A_SKILL.md](docs/ADDING_A_SKILL.md) | Complete skill authoring guide with examples |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | GitHub → Hugging Face Spaces deployment pipeline |
| [SKILL_AND_AGENT_REFERENCE.md](docs/SKILL_AND_AGENT_REFERENCE.md) | File-by-file reference for skill and agent packages |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contributor guidelines and conventions |

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

<div align="center">

**[Live Demo](https://sarveshtalele-mcp-skills-registry.hf.space)** · **[Report a Bug](https://github.com/sarveshtalele/mcp-skills-registry/issues/new?labels=bug)** · **[Request a Feature](https://github.com/sarveshtalele/mcp-skills-registry/issues/new?labels=enhancement)**

Made with ❤️ by [Sarvesh Talele](https://github.com/sarveshtalele)

</div>
