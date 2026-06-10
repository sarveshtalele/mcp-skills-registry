# Deployment: GitHub → Hugging Face Spaces

The project is developed on GitHub and hosted on a Hugging Face **Docker Space**.
A GitHub Action mirrors `main` to the Space, which rebuilds from the `Dockerfile`
and serves the MCP server.

```
GitHub (source of truth)  --push main-->  HF Space (Docker build)  -->  live MCP server
        │                                        │
   CI: lint + test                       Dockerfile → uvicorn :7860
```

## 1. Create the Hugging Face Space

1. https://huggingface.co/new-space
2. Owner: your account/org · Space name: `mcp-skill-registry`
3. **SDK: Docker** · Hardware: CPU basic (free) is enough to start.
4. Create. Note the URL: `https://huggingface.co/spaces/<user>/mcp-skill-registry`.

The Space reads the YAML header in `README.md` (`sdk: docker`, `app_port: 7860`).

## 2. Create a write token

Hugging Face → Settings → Access Tokens → **New token** (role: *write*). Copy it.

## 3. Wire up GitHub → HF sync

In the GitHub repo → Settings:

- **Secrets and variables → Actions → Secrets**: add `HF_TOKEN` = the write token.
- **Variables**: add `HF_USERNAME` (your HF handle) and `HF_SPACE`
  (`mcp-skill-registry`).

`.github/workflows/deploy-hf.yml` force-pushes `main` to the Space on every push.

## 4. Push

```bash
git remote add origin https://github.com/<user>/mcp-skills-registry.git
git push -u origin main
```

CI runs lint + tests; on success, the deploy job mirrors to the Space, which
builds the image and starts `uvicorn skill_registry.main:app` on port 7860.

## 5. Verify

```bash
SPACE=https://<user>-mcp-skill-registry.hf.space
curl $SPACE/health
curl -X POST $SPACE/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

## Persistent storage

SQLite lives at `/data/registry.db` (set by `SKILLREG_DB_PATH` in the Dockerfile).
Enable **persistent storage** on the Space so execution history and the audit log
survive restarts. Skills are baked into the image from `skills/`, so they redeploy
with each build.

## Manual deploy (no GitHub)

```bash
pip install huggingface_hub
huggingface-cli login
huggingface-cli upload <user>/mcp-skill-registry . . --repo-type space
```

## Configuration

All settings are environment variables with the `SKILLREG_` prefix (see
`.env.example`). Set them as **Space secrets/variables** to override defaults —
e.g. `SKILLREG_ENABLE_SEMANTIC_SEARCH=true` (requires the `search` extra in the
image).
