---
name: legacy-discovery
version: 1.0.0
description: >
  Reverse-engineer a legacy application. Scans a local repository path (or works from a
  description) to inventory languages, entry points, and modules, then produces a spec.md and
  architecture.md scaffold. Trigger on: analyse legacy app, reverse engineer, discovery,
  inventory codebase, modernization discovery.
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
    required: false
    default: "."
    description: Local repo path to scan (optional).
  - name: app_description
    type: string
    required: false
    description: Description of the app if no path given.
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
