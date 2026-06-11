---
name: ui-modernization
version: 1.0.0
description: >
  Plan migration of a legacy UI to a modern React component architecture. Produces a component
  inventory, a target component tree, and starter React + test stubs. Trigger on: modernize
  UI, convert to React, UI migration, frontend modernization.
author: sarveshtalele
license: MIT
category: frontend
tags: [frontend, react, ui, modernization]
execution:
  type: python-script
  entrypoint: scripts/main.py:run
  timeout_seconds: 20
inputs:
  - name: screens
    type: array
    items: string
    required: true
    description: List of legacy screen/page names.
  - name: framework
    type: string
    required: false
    default: "react"
    description: Target framework.
outputs:
  - name: plan_markdown
    type: string
    description: UI modernization plan.
  - name: components
    type: array
    description: Proposed component list.
  - name: sample_component
    type: string
    description: Starter component stub.
status: active
---

# ui-modernization

Plan a legacy UI migration to a modern component framework (React by default):
component inventory, target tree, and starter stubs.

## When to use
When modernizing a front end. Triggers: *modernize UI, convert to React, UI
migration, frontend modernization*.

## Inputs
- `screens` (array of strings, required) — legacy screen/page names.
- `framework` (string, optional, default `react`).

## Outputs
- `plan_markdown` — inventory, target tree, approach, definition of done.
- `components` — derived component names.
- `sample_component` — a starter component stub.

## How it works
Derives PascalCase component names from screen names, builds a target tree, and
emits a strangler migration approach with a per-screen DoD.

## User stories
- *As a front-end lead*, I get a component map and a sample to start porting.

## Edge cases
- A single screen passed as a string is accepted.
- Empty screen list → clear error (nothing to plan).
- Messy names with punctuation → sanitised into valid component identifiers.

## Files
See [DOCS.md](DOCS.md). Figma mapping guidance lives in `figma/`.
