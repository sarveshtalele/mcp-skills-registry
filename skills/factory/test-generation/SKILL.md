---
name: test-generation
version: 1.0.0
description: >
  Generate a test strategy and starter test stubs for given modules across unit, integration,
  and e2e layers (pytest/jest/playwright). Trigger on: generate tests, test plan, test
  strategy, coverage plan, test scaffolding.
author: sarveshtalele
license: MIT
category: quality
tags: [testing, quality, jest, playwright, pytest]
execution:
  type: python-script
  entrypoint: scripts/main.py:run
  timeout_seconds: 20
inputs:
  - name: modules
    type: array
    items: string
    required: true
    description: Modules/features to test.
  - name: frameworks
    type: array
    items: string
    required: false
    description: Preferred test frameworks.
outputs:
  - name: test_plan_markdown
    type: string
    description: The test strategy.
  - name: stubs
    type: object
    description: Starter test stubs by layer.
status: active
---

# test-generation

Produce a layered test strategy (unit/integration/e2e) and starter stubs for the
given modules across pytest, jest, and playwright.

## When to use
When establishing or improving test coverage. Triggers: *generate tests, test
plan, coverage plan, test scaffolding*.

## Inputs
- `modules` (array of strings, required).
- `frameworks` (array, optional, default `[pytest, jest, playwright]`).

## Outputs
- `test_plan_markdown` — pyramid, coverage matrix, targets.
- `stubs` — starter tests per module per framework.

## How it works
Builds a coverage matrix for the modules and emits idiomatic stubs per requested
framework from the templates in `jest_templates/` and `playwright_templates/`.

## User stories
- *As an engineer*, I get a coverage plan and runnable stubs to fill in.

## Edge cases
- A single module string is accepted.
- Empty modules → clear error.
- Unknown frameworks are ignored gracefully.

## Files
See [DOCS.md](DOCS.md).
