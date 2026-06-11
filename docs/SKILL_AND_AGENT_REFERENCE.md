# Skill & Agent File Reference

This document explains **every file and folder** in a skill or agent package, how
the registry uses it, and the upload/validation rules.

---

## Skill folder architecture

A full, production-grade skill (e.g. `skills/factory/legacy-discovery/`):

```
skill-name/
├── SKILL.md            # REQUIRED — manifest (YAML frontmatter) + agent instructions
├── manifest.yaml       # machine-readable mirror of the manifest (for external tooling)
├── mcp.json            # optional MCP tool descriptor (name + inputSchema)
├── scripts/
│   ├── __init__.py     # marks scripts/ importable
│   └── main.py         # REQUIRED for python-script skills: run(inputs) -> dict
├── references/         # background docs (human reference, not executed)
├── templates/          # output templates the script fills in
├── schemas/            # JSON Schemas describing inputs/outputs
├── examples/           # example outputs / fixtures
├── tests/              # skill-local smoke tests (pytest)
└── DOCS.md             # per-skill file reference
```

### What each file does

| Path | Required | Read by registry | Purpose |
|------|----------|------------------|---------|
| `SKILL.md` | ✅ | ✅ (frontmatter → MCP tool schema; body → agent guidance) | The single source of truth. |
| `manifest.yaml` | — | — | A YAML mirror for external pipelines; the registry ignores it. |
| `mcp.json` | — | — | Pre-rendered MCP descriptor for clients that prefer a static file. |
| `scripts/main.py` | ✅ for runnable skills | executed | Exposes `run(inputs: dict) -> dict`; runs in an isolated subprocess. |
| `scripts/__init__.py` | — | — | Lets `main.py` import siblings (e.g. `engine/`). |
| `references/` | — | — | Method notes, patterns, domain docs. |
| `templates/` | — | — | `*.tpl` patterns the entrypoint expands. |
| `schemas/` | — | — | JSON Schema for output validation by consumers. |
| `examples/` | — | — | Sample outputs to illustrate the contract. |
| `tests/` | — | — (not collected by server CI) | `pytest` smoke tests for skill authors. |
| `DOCS.md` | — | — | Human reference for the skill's files. |

Only `SKILL.md` is mandatory for discovery; `scripts/main.py` is required to
*execute*. Everything else is supporting material.

### `SKILL.md` frontmatter (manifest)

```yaml
---
name: my-skill            # coerced to a lowercase slug if needed
version: 1.0.0            # coerced to 0.0.0 if not semantic
description: ...
category: ...
tags: [...]
execution:
  type: python-script     # python-script (runnable) | prompt-based
  entrypoint: scripts/main.py:run   # coerced to default if malformed
  timeout_seconds: 30
inputs:  [ {name, type, required, default, items, enum, description} ]
outputs: [ {name, type, description} ]
---
(body = agent instructions)
```

---

## Agent folder architecture

A full agent (e.g. `agents/gatekeeper/`):

```
agent-name/
├── AGENT.md          # REQUIRED — manifest (frontmatter) + system instructions
├── system-prompt.md  # the agent's role/system prompt
├── workflow.yaml     # ordered steps; each `uses` references a skill
├── skills.yaml       # the skills this agent orchestrates
├── tools.yaml        # external tools / MCP servers the agent may use
├── governance.yaml   # (gatekeeper only) gate policy + thresholds
└── DOCS.md           # per-agent file reference
```

| File | Required | Read by registry | Purpose |
|------|----------|------------------|---------|
| `AGENT.md` | ✅ | ✅ (frontmatter `skills`, `workflow`) | Source of truth for the agent. |
| `system-prompt.md` | — | — | Role prompt for the client to load. |
| `workflow.yaml` | — | — | Machine-readable step sequence. |
| `skills.yaml` | — | — | Declares orchestrated skills. |
| `tools.yaml` | — | — | Declares external tools. |
| `governance.yaml` | — | — | Gate policy (gatekeeper). |
| `DOCS.md` | — | — | Human reference. |

---

## Upload, validation & extraction rules

Uploads are **permissive by design** — they inform rather than block:

1. **Nested-folder auto-detect.** The archive's `SKILL.md`/`AGENT.md` location
   defines the package root. Both `my-skill/SKILL.md` (wrapped) and a flat
   `SKILL.md` work; the wrapper folder is stripped on install.
2. **Coercion, not rejection.** A non-slug `name` is slugified, a non-semantic
   `version` becomes `0.0.0`, a malformed `entrypoint` falls back to the default.
   The upload still succeeds.
3. **Structure report.** The response lists `installed_files` (the exact tree
   written) plus non-blocking `warnings` (e.g. missing entrypoint, no description).
4. **Hard errors only when unusable.** No archive, not a zip, no manifest at all,
   zip-slip/zip-bomb → rejected with a clear message.

### Manage skills & agents

| Action | REST | UI |
|--------|------|----|
| Upload / re-upload | `POST /api/v1/skills/upload` (overwrite defaults true) | Upload tab |
| Validate only | `POST /api/v1/skills/validate` | "Validate format" |
| Delete | `DELETE /api/v1/skills/{name}` | Delete on card |
| Same for agents | `…/agents/…` | Agent tab |

Re-uploading a name overwrites it in place. Deleting removes the folder and
refreshes the catalogue immediately.
