---
name: legacy-discovery
version: 1.0.0
description: >
  Inventory a LOCAL codebase on the server filesystem. Use ONLY with a local
  `repo_path`; this skill does NOT clone or fetch remote repositories — for a
  github.com URL use the `reverse-engineering` skill instead. Scans the path for
  languages, entry points, and module counts and returns spec.md + architecture.md
  scaffolds. The returned object is the authoritative result; do not supplement it
  with web search, prior memory, or assumptions. Trigger on: inventory a local repo
  path, scan this directory, modernization discovery of a local codebase.
author: sarveshtalele
license: MIT
category: modernization
tags: [modernization, legacy, discovery, architecture]
execution:
  type: python-script
  entrypoint: scripts/main.py:run
  timeout_seconds: 60
inputs:
  - name: repo_path
    type: string
    required: true
    description: >
      Absolute path to a LOCAL directory the server can read. Not a URL. If the
      path is missing or unreadable the skill returns a clear error.
outputs:
  - name: spec_markdown
    type: string
    description: Specification scaffold.
  - name: architecture_markdown
    type: string
    description: Architecture overview.
  - name: inventory
    type: object
    description: Detected languages and counts.
status: active
---

# legacy-discovery

Reverse-engineer a legacy application into a reviewable specification and an
as-is architecture document, with a language/entry-point inventory.

## When to use
Deployment/Release or Discovery SDLC phase, when you need to understand an
existing system before modernizing it. Triggers: *analyse legacy app, reverse
engineer, inventory codebase, modernization discovery*.

## Inputs
- `repo_path` (string, optional) — local path to scan. Defaults to `.`.
- `app_description` (string, optional) — used when no path is available.

## Outputs
- `spec_markdown` — specification scaffold with `[NEEDS CLARIFICATION]` markers.
- `architecture_markdown` — as-is architecture overview.
- `inventory` — `{languages, entry_points, module_count}`.

## How it works
1. If `repo_path` is a directory, walk it (skipping VCS/build/vendor dirs).
2. Classify files by extension into languages; detect candidate entry points.
3. Emit a spec + architecture scaffold seeded with what was detected.

## User stories
- *As an architect*, I scan a repo and get a starting spec so I don't begin from
  a blank page.
- *As a tech lead*, I see the language mix and entry points to scope the work.

## Edge cases
- No path and no description → scaffolds with explicit clarification markers.
- Path does not exist → falls back to description-only mode.
- Binary-heavy or empty repos → `inventory` reports zero modules, no crash.

## Files
See [DOCS.md](DOCS.md) for what every file in this skill does.
