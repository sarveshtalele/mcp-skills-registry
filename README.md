---
title: MCP Skill Registry
emoji: 🧩
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# MCP Skill Registry

A centralized, Hugging Face-hosted **MCP server** for discovering and executing
community **skills**. Skills are self-contained folders (`SKILL.md` + code) that
the server auto-discovers and exposes both as **MCP tools** and over a plain
**REST API**.

> The YAML block above is Hugging Face Spaces metadata. On GitHub it renders as a
> table; on a Space it configures the Docker runtime. Leave it in place.

## Why

- **Add a skill by dropping a folder.** No code changes to the server — follow the
  [skill folder structure](skills/README.md) and reload.
- **One catalogue, two surfaces.** Every skill is callable via MCP (`tools/list`,
  `tools/call`) and via REST (`/api/v1/skills/...`).
- **Safe execution.** Each skill runs in an isolated subprocess with a hard timeout
  and output-size cap.
- **Modular, tested, PEP 8.** Clean layering (models → db → repositories → services
  → api), full test suite, ruff + black + mypy configured.

## Architecture

```
src/skill_registry/
├── config.py          # env-driven settings (pydantic-settings)
├── container.py       # composition root (wires the object graph)
├── main.py            # FastAPI app factory + entrypoints
├── models/            # pydantic domain models
├── db/                # SQLite wrapper + schema.sql
├── repositories/      # persistence (executions, audit)
├── services/          # loader, validator, executor, search, audit, registry
├── mcp/               # JSON-RPC 2.0 MCP protocol handler
└── api/               # FastAPI routers: health, mcp, rest

skills/                # self-contained skills, auto-discovered (see skills/README.md)
scripts/new_skill.py   # scaffolder
tests/                 # pytest suite
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design.

## Quick start (local)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # add ".[dev,search]" for semantic search
skill-registry                   # serves on http://localhost:7860
```

```bash
curl http://localhost:7860/health
curl http://localhost:7860/api/v1/skills
curl -X POST http://localhost:7860/api/v1/skills/text-statistics/execute \
  -H 'Content-Type: application/json' \
  -d '{"inputs": {"text": "The quick brown fox jumps over the lazy dog."}}'
```

## MCP endpoint

Implements the **Streamable HTTP** transport (JSON-RPC 2.0) at `/mcp`:

- `POST /mcp` — `initialize`, `tools/list`, `tools/call`, `ping` (single or batch).
  `initialize` returns an `Mcp-Session-Id` header; echo it on later requests.
- `GET /mcp` — `405` (no server-initiated stream; spec-permitted).
- `DELETE /mcp` — terminate the session.

```bash
curl -X POST http://localhost:7860/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

### Connect a client

```bash
# Claude Code — native HTTP transport (no bridge needed)
claude mcp add --transport http skill-registry https://<user>-mcp-skill-registry.hf.space/mcp
```

```jsonc
// VS Code — .vscode/mcp.json
{ "servers": { "skill-registry": {
  "type": "http", "url": "https://<user>-mcp-skill-registry.hf.space/mcp" } } }
```

Claude Desktop: Settings → Connectors → add a custom remote MCP server with the
`/mcp` URL. (Older stdio-only clients can bridge via
`npx -y mcp-remote <url>`.)

## Add a skill

Three ways — pick by audience:

```bash
# 1. Scaffold locally, then reload
python scripts/new_skill.py my-skill          # creates skills/my-skill/
curl -X POST http://localhost:7860/api/v1/admin/reload

# 2. Upload a packaged skill (no Git, no restart)
zip -r my-skill.zip my-skill/                  # archive must contain SKILL.md
curl -X POST http://localhost:7860/api/v1/skills/upload \
  -F 'file=@my-skill.zip'                       # add ?overwrite=true to replace

# 3. Open a PR adding skills/my-skill/ — CI tests it, merge deploys it to HF
```

Full guide: [docs/ADDING_A_SKILL.md](docs/ADDING_A_SKILL.md).

## Deploy (GitHub → Hugging Face)

Push to GitHub; CI mirrors `main` to a Hugging Face Space that builds the
`Dockerfile`. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Development

```bash
make install   # editable install with dev extras
make test      # pytest
make lint      # ruff + black --check
make format    # ruff --fix + black
make run       # local dev server
```

## License

MIT — see [LICENSE](LICENSE).
