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

Generate a test strategy and starter test stubs for given modules across unit, integration, and e2e layers (pytest/jest/playwright). Trigger on: generate tests, test plan, test strategy, coverage plan, test scaffolding.
