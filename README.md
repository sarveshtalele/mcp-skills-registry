<div align="center">

# 🧩 MCP Skill Registry

**A self-hostable [Model Context Protocol](https://modelcontextprotocol.io) server that turns a folder of "skills" into tools any MCP client can discover and run.**

[![CI](https://github.com/sarveshtalele/mcp-skills-registry/actions/workflows/ci.yml/badge.svg)](https://github.com/sarveshtalele/mcp-skills-registry/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[What it does](#-what-it-does) · [How it works](#-how-it-works) · [Connect a client](#-connect-an-mcp-client) · [Authoring skills](#-authoring-a-skill) · [Deployment](#-deployment)

</div>

---

## 🎯 What It Does

**MCP Skill Registry** is one server that hosts many *skills* and exposes each one as a callable tool.

A **skill** is just a folder containing a `SKILL.md` manifest and a small script. Drop the folder in, and the server:

1. **Discovers** it automatically (reads the manifest at startup).
2. **Publishes** it on two interfaces at once:
   - as an **MCP tool** — usable from Claude Code, Claude Desktop, VS Code, or any MCP client;
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
   ┌─────────────┐     POST /api/v1/...      │   skills/<name>/    │
   │ REST caller │ ◄────────────────────────►│   folder           │
   └─────────────┘                           └─────────┬──────────┘
                                                       │ runs in
                                                       ▼ subprocess
                                          skills/text-statistics/
                                          skills/your-skill/ ...
```

---

## ⚙️ How It Works

### Architecture

The server is a small, layered FastAPI application. Each layer depends only on the
layers beneath it, so it stays testable and easy to extend.

```text
┌──────────────────────────────────────────────────────────────────────┐
│                     FastAPI application  (port 7860)                   │
│                                                                        │
│   api/        Routers:  /  ·  /health  ·  /mcp  ·  /api/v1/skills      │  ← transport
│     │                                                                  │
│   mcp/        Streamable HTTP transport · JSON-RPC 2.0 · sessions      │  ← MCP protocol
│     │                                                                  │
│   services/   SkillRegistry (facade)                                   │  ← application
│     │           ├─ loader      parse & validate SKILL.md               │     logic
│     │           ├─ validator   check inputs against the manifest       │
│     │           ├─ executor    run skill in a sandboxed subprocess     │
│     │           ├─ search      keyword / optional semantic ranking     │
│     │           ├─ installer   safe ZIP upload (zip-slip / bomb guard) │
│     │           └─ audit       append-only event log                   │
│     │                                                                  │
│   repositories/  execution history · audit trail                      │  ← persistence
│     │                                                                  │
│   db/  models/  config/  container/  main                              │  ← storage, types,
│         SQLite + schema.sql · pydantic models · settings · wiring      │     wiring
└───────────────────────────────┬────────────────────────────────────── ┘
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

**Why subprocesses?** Process-level isolation, a clean import namespace per call,
and a reliable hard timeout — a misbehaving skill can never hang or crash the server.

Each skill's entrypoint is a single function:

```python
def run(inputs: dict) -> dict:
    ...  # inputs are pre-validated; return a JSON-serializable dict
```

---

## ✨ Features

- **🔌 Dual interface** — every skill is an MCP tool *and* a REST resource.
- **🧭 Zero-config discovery** — skills are plain folders; no registration code.
- **🛡️ Sandboxed execution** — subprocess isolation, per-skill timeouts, output caps.
- **📤 Live uploads** — install a skill from a ZIP via the API; no restart.
- **🌐 Native MCP** — Streamable HTTP transport with sessions; no bridge needed.
- **🔍 Search** — keyword out of the box, optional semantic (vector) search.
- **🧱 Clean codebase** — layered, typed, 37 tests, CI on Python 3.10–3.12.

---

## 🚀 Quick Start (local)

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

**Live on Hugging Face:** https://huggingface.co/spaces/sarveshtalele/mcp-skills-registry

> **Two URLs, two purposes.** The Space page above is where you *open the app* (the
> upload UI loads there). MCP/REST clients, however, connect to the **app host** that
> Hugging Face serves the running container on:
> `https://sarveshtalele-mcp-skills-registry.hf.space`. The API is **not** reachable
> under `huggingface.co/spaces/...` — that path serves the website, not the container.

---

## 🔗 Connect an MCP Client

The server speaks the **Streamable HTTP** MCP transport at `/mcp`, so modern clients
connect directly. Use your local URL (`http://localhost:7860/mcp`) or the hosted
**app host** (`https://sarveshtalele-mcp-skills-registry.hf.space/mcp`).

### Claude Code

```bash
claude mcp add --transport http skill-registry \
  https://sarveshtalele-mcp-skills-registry.hf.space/mcp
```

Verify inside a session:

```text
/mcp          # lists connected servers and their tools
```

Remove it again with `claude mcp remove skill-registry`.

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
| --- | --- |
| `POST /mcp` | `initialize`, `tools/list`, `tools/call`, `ping` (single or batch). |
| `GET /mcp` | `405` — no server-initiated stream (spec-permitted). |
| `DELETE /mcp` | Terminate the session in the `Mcp-Session-Id` header. |

---

## 🧰 REST API

Prefer plain HTTP? Every skill is reachable without MCP.

| Method & Path | Description |
| --- | --- |
| `GET /` | Service metadata + entry points. |
| `GET /health` | Liveness probe + skill count. |
| `GET /api/v1/skills` | List / search skills (`q`, `category`, `limit`, `offset`). |
| `GET /api/v1/skills/{name}` | Full skill manifest. |
| `POST /api/v1/skills/{name}/execute` | Run a skill — body `{"inputs": {...}}`. |
| `POST /api/v1/skills/upload` | Install a skill from a ZIP (`?overwrite=true`). |
| `POST /api/v1/admin/reload` | Re-scan the skills directory. |

Interactive Swagger UI is served at `/docs`.

```bash
curl -X POST http://localhost:7860/api/v1/skills/text-statistics/execute \
  -H 'Content-Type: application/json' \
  -d '{"inputs": {"text": "The quick brown fox jumps over the lazy dog."}}'
```

---

## 🖥️ Upload UI

An Apple-styled web UI is served at **`/ui`** (Gradio, mounted in-process). Upload a
skill `.zip`, click **Validate** to check it matches the required format, then
**Upload & Publish** to install it. When a GitHub token is configured
(`SKILLREG_GITHUB_TOKEN`), publishing also commits the skill to the repo's
`skills/` folder, which redeploys the Space — so the upload becomes permanent.

Open it on Hugging Face: **https://huggingface.co/spaces/sarveshtalele/mcp-skills-registry**
(the UI is the Space's landing page).

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

**1. Scaffold**

```bash
python scripts/new_skill.py my-skill
```

**2. `SKILL.md`**

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

**3. `scripts/main.py`**

```python
def run(inputs: dict) -> dict:
    return {"result": inputs["text"].upper()}
```

**4. Register**

```bash
curl -X POST http://localhost:7860/api/v1/admin/reload      # local rescan
# or upload a packaged skill (no restart):
zip -r my-skill.zip my-skill/
curl -X POST http://localhost:7860/api/v1/skills/upload -F 'file=@my-skill.zip'
```

Full guide: **[docs/ADDING_A_SKILL.md](docs/ADDING_A_SKILL.md)**.

---

## 🌍 Deployment

Runs anywhere Docker runs, and ships to a **Hugging Face Docker Space** out of the box.

```bash
docker build -t mcp-skill-registry .
docker run -p 7860:7860 -v "$(pwd)/data:/data" mcp-skill-registry
```

Pushing to `main` on GitHub auto-mirrors to the Space, which rebuilds from the
`Dockerfile`. Full instructions (tokens, persistence): **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**.

---

## 🔧 Configuration

Environment variables, prefixed `SKILLREG_` (see [.env.example](.env.example)):

| Variable | Default | Description |
| --- | --- | --- |
| `SKILLREG_PORT` | `7860` | HTTP port. |
| `SKILLREG_SKILLS_DIR` | `skills` | Skill catalogue directory. |
| `SKILLREG_DB_PATH` | `data/registry.db` | SQLite path. |
| `SKILLREG_DEFAULT_TIMEOUT_SECONDS` | `30` | Default execution timeout. |
| `SKILLREG_MAX_TIMEOUT_SECONDS` | `120` | Upper bound on any timeout. |
| `SKILLREG_ENABLE_UPLOADS` | `true` | Allow the upload endpoint. |
| `SKILLREG_ENABLE_SEMANTIC_SEARCH` | `false` | Vector search (needs the `search` extra). |

---

## 🧪 Development

```bash
make install   # editable install with dev extras
make test      # pytest (37 tests)
make lint      # ruff + black --check
make format    # ruff --fix + black
make run       # local dev server
```

CI runs lint + tests on Python 3.10, 3.11, and 3.12.

---

## 📁 Project Structure

```text
mcp-skills-registry/
├── src/skill_registry/     # the server (layered package)
│   ├── api/  mcp/  services/  repositories/  db/  models/
│   └── config.py · container.py · main.py
├── skills/                 # self-contained skills (auto-discovered)
│   ├── _template/          # scaffold skeleton
│   └── text-statistics/    # worked example
├── scripts/                # new_skill.py · HF entrypoint
├── tests/                  # pytest suite
├── docs/                   # architecture · deployment · authoring
└── Dockerfile · pyproject.toml · Makefile · .github/workflows/
```

---

## 📄 License

MIT — see [LICENSE](LICENSE).
