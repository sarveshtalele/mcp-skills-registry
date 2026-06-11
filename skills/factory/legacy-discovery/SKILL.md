---
name: legacy-discovery
version: 2.0.0
description: >
  Reverse-engineer / discover a codebase. Works in two modes — provide EXACTLY one
  input: `repo_url` (a github.com URL) clones the repo server-side and runs full
  static analysis, producing a System Design Document, architecture + dependency
  overview, and a 100-point quality score; `repo_path` (a local directory the
  server can read) inventories languages, entry points, and modules and returns
  spec + architecture scaffolds. The returned object is the authoritative analysis
  — rely on it and do not supplement with web search or prior memory. Trigger on:
  reverse engineer, analyse this repo, discovery, inventory a codebase, generate an
  SDD, explain this repository, modernization discovery.
author: sarveshtalele
license: MIT
category: software-engineering
tags: [reverse-engineering, discovery, architecture, static-analysis, modernization]
execution:
  type: python-script
  entrypoint: scripts/main.py:run
  timeout_seconds: 120
inputs:
  - name: repo_url
    type: string
    required: false
    description: >
      A public github.com URL to clone and analyse (remote mode). Provide this OR
      repo_path, not both.
  - name: repo_path
    type: string
    required: false
    description: >
      A local directory the server can read (local mode). Provide this OR repo_url.
outputs:
  - name: mode
    type: string
    description: Either remote (URL clone + SDD) or local (filesystem scan).
  - name: report_markdown
    type: string
    description: Remote mode — the generated architectural report (size-capped).
  - name: manifest
    type: object
    description: Remote mode — run record with metrics and generated-file metadata.
  - name: spec_markdown
    type: string
    description: Local mode — specification scaffold.
  - name: architecture_markdown
    type: string
    description: Local mode — as-is architecture overview.
  - name: inventory
    type: object
    description: Local mode — detected languages, entry points, module count.
status: active
---

# legacy-discovery

Discover and reverse-engineer a codebase — one skill, two modes.

## When to use
- You have a **github.com URL** → pass `repo_url` (remote: clone + full SDD).
- You have a **local directory** the server can read → pass `repo_path` (local scan).

Provide exactly one. Passing neither, or both, returns a clear error.

## Outputs
- `mode` — `remote` or `local`.
- Remote: `manifest`, `report_markdown`, `sdd_available`.
- Local: `spec_markdown`, `architecture_markdown`, `inventory`.

## Guardrails
The returned object is the complete analysis. Do not supplement it with web
search, external fetches, or prior memory — report exactly what the skill returns.

## User stories
- *As an architect*, I point at a GitHub URL and get an SDD without cloning by hand.
- *As a maintainer*, I scan a local checkout to inventory its stack and entry points.

## Edge cases
- Neither input → error asking for `repo_url` or `repo_path`.
- Both inputs → error (ambiguous).
- `repo_path` not a directory → clear error suggesting `repo_url` for remotes.

See the analysis `engine/` under `scripts/` for the remote-mode pipeline.
