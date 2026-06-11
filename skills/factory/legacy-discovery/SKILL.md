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

Reverse-engineer a legacy application. Scans a local repository path (or works from a description) to inventory languages, entry points, and modules, then produces a spec.md and architecture.md scaffold. Trigger on: analyse legacy app, reverse engineer, discovery, inventory codebase, modernization discovery.
