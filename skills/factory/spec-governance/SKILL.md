---
name: spec-governance
version: 1.0.0
description: >
  Validate a set of engineering artifacts against governance rules and emit a deterministic
  pass/fail audit report with a compliance score. Trigger on: governance check, compliance
  audit, validate spec, gate, review compliance.
author: sarveshtalele
license: MIT
category: governance
tags: [governance, compliance, audit, review]
execution:
  type: python-script
  entrypoint: scripts/main.py:run
  timeout_seconds: 20
inputs:
  - name: artifacts_present
    type: array
    items: string
    required: true
    description: Artifact names that exist (e.g. spec.md, plan.md, tests).
  - name: spec_text
    type: string
    required: false
    description: Optional spec text to scan for required sections.
outputs:
  - name: audit_markdown
    type: string
    description: The audit report.
  - name: score
    type: integer
    description: Compliance score 0-100.
  - name: passed
    type: boolean
    description: Whether the gate passes.
status: active
---

# spec-governance

Validate a set of engineering artifacts against governance rules and emit a deterministic pass/fail audit report with a compliance score. Trigger on: governance check, compliance audit, validate spec, gate, review compliance.
