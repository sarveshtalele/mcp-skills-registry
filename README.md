<div align="center">

# 🧩 MCP Skill Registry

**A centralized, self-hostable [Model Context Protocol](https://modelcontextprotocol.io) server for discovering, sharing, and executing community skills.**

[![CI](https://github.com/sarveshtalele/mcp-skills-registry/actions/workflows/ci.yml/badge.svg)](https://github.com/sarveshtalele/mcp-skills-registry/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linter: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Hugging Face Space](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Space-blue)](https://huggingface.co/spaces/sarveshtalele/mcp-skills-registry)

[Quick Start](#-quick-start) · [Architecture](#-architecture) · [Usage](#-usage) · [Authoring Skills](#-authoring-a-skill) · [Deployment](#-deployment) · [API Reference](#-api-reference) · [Contributing](#-contributing)

</div>

---

## 📖 Overview

**MCP Skill Registry** turns a folder of self-contained "skills" into a live MCP
server. Each skill is a directory with a `SKILL.md` manifest and an executable
entrypoint; the server auto-discovers them and exposes every one as both an **MCP
tool** (for clients like Claude Desktop, Claude Code, and VS Code) and a **REST
endpoint** (for scripts and integrations).

Skills run in **isolated subprocesses** with hard timeouts and output caps, so a
misbehaving skill can never take down the server. New skills can be added three
ways — drop a folder, upload a ZIP over the API, or open a pull request — with
**zero changes to the server code**.

### Why this exists

| Problem | This project |
| --- | --- |
| Skills scattered across repos, hard to discover | One catalogue, searchable via API and MCP |
| Every integration re-implements tool plumbing | Author once; callable from any MCP client *and* REST |
| Running untrusted code is risky | Subprocess isolation, timeouts, output caps, upload validation |
| Adding capability means editing the server | Drop a folder or POST a ZIP — no server changes |
| "Works on my machine" deployment | One `Dockerfile`, one-command deploy to Hugging Face |

---

## ✨ Features

- **🔌 Dual interface** — every skill is simultaneously an MCP tool and a REST resource.
- **🧭 Auto-discovery** — skills are plain folders; the server reads `SKILL.md` at startup.
- **🛡️ Sandboxed execution** — out-of-process runs with per-skill timeouts and output-size limits.
- **📤 Live uploads** — install a skill from a ZIP via the API; no restart, with zip-slip / zip-bomb protection.
- **🔍 Discovery** — keyword search out of the box; optional semantic (vector) search.
- **🌐 Streamable HTTP MCP** — implements the 2025 MCP transport with session management; connect natively, no bridge.
- **📝 Audit trail** — every execution and catalogue change is recorded in SQLite.
- **🧱 Clean architecture** — layered package, fully typed, 36 tests, CI on Python 3.10–3.12.

---

## 🏗 Architecture

```text
                         ┌──────────────────────────────────────────────┐
   MCP client            │            FastAPI application (:7860)        │
 (Claude / VS Code) ─────┤  api/      health · mcp (Streamable HTTP) ·   │
                         │            rest                              │
   REST caller     ──────┤  mcp/      JSON-RPC handler · sessions        │
 (curl / scripts)        │  services/ registry · loader · validator ·    │
                         │            executor · search · installer ·    │
   ZIP upload      ──────┤            audit                             │
                         │  repositories/  executions · audit (SQLite)   │
                         │  db/ models/ config/ container                │
                         └───────────────┬──────────────────────────────┘
                                         │ discovers + runs
                         ┌───────────────▼──────────────────────────────┐
                         │  skills/   self-contained skill folders        │
                         │     text-statistics/  SKILL.md + scripts/ ...  │
                         └──────────────────────────────────────────────┘
```

**Layering (each layer depends only on those beneath it):**

| Layer | Package | Responsibility |
| --- | --- | --- |
| Transport | `api/` | FastAPI routers: health, MCP, REST |
| Protocol | `mcp/` | JSON-RPC 2.0 + session management |
| Application | `services/` | Discovery, validation, execution, search, install, audit |
| Persistence | `repositories/` | Execution history + audit trail |
| Storage | `db/` | SQLite wrapper + `schema.sql` |
| Shared | `models/`, `config.py` | Pydantic models, env-driven settings |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design and rationale.

---

## 🚀 Quick Start

### Prerequisites

- Python **3.10+**
- `git`

### Local install

```bash
git clone https://github.com/sarveshtalele/mcp-skills-registry.git
cd mcp-skills-registry

python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # add ".[dev,search]" for semantic search

skill-registry                   # serves on http://localhost:7860
```

### Verify

```bash
curl http://localhost:7860/health
# {"status":"ok","version":"0.2.0","skills_loaded":1}

curl -X POST http://localhost:7860/api/v1/skills/text-statistics/execute \
  -H 'Content-Type: application/json' \
  -d '{"inputs": {"text": "The quick brown fox jumps over the lazy dog."}}'
```

### Run with Docker

```bash
docker build -t mcp-skill-registry .
docker run -p 7860:7860 -v "$(pwd)/data:/data" mcp-skill-registry
```

---

## 🔧 Usage

### Connect an MCP client

The server implements the **Streamable HTTP** transport at `/mcp`, so modern
clients connect directly — no `mcp-remote` bridge required.

**Claude Code**

```bash
claude mcp add --transport http skill-registry \
  https://sarveshtalele-mcp-skills-registry.hf.space/mcp
```

**VS Code** — `.vscode/mcp.json`

```jsonc
{
  "servers": {
    "skill-registry": {
      "type": "http",
      "url": "https://sarveshtalele-mcp-skills-registry.hf.space/mcp"
    }
  }
}
```

**Claude Desktop** — Settings → Connectors → add a custom remote MCP server with
the `/mcp` URL. (Older stdio-only clients can bridge with
`npx -y mcp-remote <url>`.)

Once connected, the client lists every skill as a tool and calls them automatically.

### Call over REST

```bash
# List / search
curl "http://localhost:7860/api/v1/skills?q=readability"

# Inspect a skill
curl http://localhost:7860/api/v1/skills/text-statistics

# Execute
curl -X POST http://localhost:7860/api/v1/skills/text-statistics/execute \
  -H 'Content-Type: application/json' \
  -d '{"inputs": {"text": "Hello world. A second sentence."}}'
```

---

## 🧩 Authoring a Skill

A skill is a single self-contained folder. This layout follows the convention
used by the
[change-impact-analysis-skill](https://github.com/sarveshtalele/change-impact-analysis-skill)
and [reverse-engineering-skill](https://github.com/sarveshtalele/reverse-engineering-skill-github-copilot):

```text
skill-name/
├── SKILL.md          # Required: YAML frontmatter (manifest) + agent instructions
├── scripts/          # Optional: executable code — entrypoint exposes run(inputs) -> dict
├── references/       # Optional: supporting documentation
├── assets/           # Optional: templates, resources, extra requirements.txt
└── ...               # Any additional files or directories
```

### 1. Scaffold

```bash
python scripts/new_skill.py my-skill
```

### 2. Define the manifest (`SKILL.md`)

```yaml
---
name: my-skill                 # lowercase slug
version: 1.0.0                 # semver
description: >
  What it does and the phrases that should trigger it.
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
Agent-facing instructions go here.
```

### 3. Implement the entrypoint (`scripts/main.py`)

```python
def run(inputs: dict) -> dict:
    """Inputs are pre-validated against SKILL.md. Return a JSON-serializable dict."""
    return {"result": inputs["text"].upper()}
```

### 4. Register it

```bash
# Local: re-scan the catalogue
curl -X POST http://localhost:7860/api/v1/admin/reload

# Or upload a packaged skill (no restart, no Git)
zip -r my-skill.zip my-skill/
curl -X POST http://localhost:7860/api/v1/skills/upload -F 'file=@my-skill.zip'
```

Full guide: **[docs/ADDING_A_SKILL.md](docs/ADDING_A_SKILL.md)**.

---

## 📡 API Reference

### MCP — `/mcp` (Streamable HTTP, JSON-RPC 2.0)

| Method | Description |
| --- | --- |
| `POST /mcp` | `initialize`, `tools/list`, `tools/call`, `ping` (single or batch). `initialize` returns an `Mcp-Session-Id` header. |
| `GET /mcp` | Returns `405` (no server-initiated stream; spec-permitted). |
| `DELETE /mcp` | Terminate the session named by `Mcp-Session-Id`. |

### REST — `/api/v1`

| Method & Path | Description |
| --- | --- |
| `GET /api/v1/skills` | List or search skills (`q`, `category`, `limit`, `offset`). |
| `GET /api/v1/skills/{name}` | Full skill manifest. |
| `POST /api/v1/skills/{name}/execute` | Execute a skill. Body: `{"inputs": {...}}`. |
| `POST /api/v1/skills/upload` | Install a skill from a ZIP (`?overwrite=true` to replace). |
| `POST /api/v1/admin/reload` | Re-scan the skills directory. |
| `GET /health` | Liveness probe + skill count. |

Interactive docs (Swagger UI) are served at `/docs` when the server is running.

---

## ⚙️ Configuration

All settings are environment variables prefixed `SKILLREG_` (see [.env.example](.env.example)).

| Variable | Default | Description |
| --- | --- | --- |
| `SKILLREG_PORT` | `7860` | HTTP port. |
| `SKILLREG_SKILLS_DIR` | `skills` | Skill catalogue directory. |
| `SKILLREG_DB_PATH` | `data/registry.db` | SQLite database path. |
| `SKILLREG_DEFAULT_TIMEOUT_SECONDS` | `30` | Default per-skill execution timeout. |
| `SKILLREG_MAX_TIMEOUT_SECONDS` | `120` | Upper bound on any skill's timeout. |
| `SKILLREG_ENABLE_UPLOADS` | `true` | Allow the upload endpoint. |
| `SKILLREG_MAX_UPLOAD_BYTES` | `5000000` | Max upload archive size. |
| `SKILLREG_ENABLE_SEMANTIC_SEARCH` | `false` | Use vector search (needs the `search` extra). |

---

## 🌍 Deployment

This repository deploys to a **Hugging Face Docker Space**. Pushing to GitHub
mirrors `main` to the Space, which rebuilds from the `Dockerfile`.

```text
GitHub (source)  ──push main──►  HF Space (docker build)  ──►  live MCP server
```

Live instance: **https://sarveshtalele-mcp-skills-registry.hf.space**

Step-by-step (tokens, secrets, persistence): **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**.

---

## 🧪 Development

```bash
make install   # editable install with dev extras
make test      # run the test suite (pytest)
make lint      # ruff + black --check
make format    # ruff --fix + black
make run       # local dev server
```

| Tool | Purpose |
| --- | --- |
| [pytest](https://pytest.org) | Test suite (36 tests). |
| [ruff](https://github.com/astral-sh/ruff) | Linting + import sorting. |
| [black](https://github.com/psf/black) | Formatting. |
| [mypy](https://mypy-lang.org) | Static typing. |

Continuous integration runs all checks on Python 3.10, 3.11, and 3.12 via
[GitHub Actions](.github/workflows/ci.yml).

---

## 📁 Project Structure

```text
mcp-skills-registry/
├── src/skill_registry/        # the server (layered package)
│   ├── api/                    # FastAPI routers (health, mcp, rest)
│   ├── mcp/                    # JSON-RPC protocol + sessions
│   ├── services/               # registry, loader, validator, executor, search, installer, audit
│   ├── repositories/           # SQLite persistence
│   ├── db/                     # database wrapper + schema.sql
│   ├── models/                 # pydantic domain models
│   ├── config.py · container.py · main.py
├── skills/                     # self-contained skills (auto-discovered)
│   ├── _template/              # scaffold skeleton
│   └── text-statistics/        # worked example
├── scripts/                    # new_skill.py scaffolder + HF entrypoint
├── tests/                      # pytest suite
├── docs/                       # architecture, deployment, authoring guides
├── Dockerfile · pyproject.toml · Makefile
└── .github/workflows/          # CI + Hugging Face deploy
```

---

## 🤝 Contributing

Contributions are welcome. Please read **[CONTRIBUTING.md](CONTRIBUTING.md)**, then:

1. Fork and create a feature branch.
2. Run `make format && make lint && make test`.
3. Open a pull request.

New skills should add a single `skills/<name>/` folder with a valid `SKILL.md`,
an entrypoint, and at least one test.

---

## 🔐 Security

- Skills execute in **isolated subprocesses** with enforced timeouts and output caps.
- Uploads are validated before being written and are protected against path
  traversal (zip-slip) and decompression bombs.
- Uploads can be disabled entirely with `SKILLREG_ENABLE_UPLOADS=false`.

Found a vulnerability? Please open a private security advisory rather than a
public issue.

---

## 🗺 Roadmap

- [ ] Per-publisher authentication and API keys
- [ ] Skill versioning with deprecation windows
- [ ] Resource limits (CPU/memory cgroups) for the execution sandbox
- [ ] Web UI for browsing and trying skills
- [ ] Skill ratings and usage analytics

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

<div align="center">
<sub>Built with FastAPI · Pydantic · the Model Context Protocol — deployed on Hugging Face Spaces.</sub>
</div>
