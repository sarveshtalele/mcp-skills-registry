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

Validate engineering artifacts against governance rules and emit a deterministic
pass/fail audit with a compliance score.

## When to use
Before a release gate. Triggers: *governance check, compliance audit, validate
spec, gate, review compliance*.

## Inputs
- `artifacts_present` (array of strings, required) — e.g. `spec.md, plan.md, tests`.
- `spec_text` (string, optional) — scanned for required sections.

## Outputs
- `audit_markdown` — the report.
- `score` (0–100), `passed` (bool, threshold 70).

## How it works
Each required artifact carries a weight (see `governance_rules/rules.yaml`);
present artifacts accumulate score. Optional spec-section checks add detail.
The gate passes at ≥ 70.

## User stories
- *As a gatekeeper*, I get an objective, repeatable pass/fail with reasons.

## Edge cases
- Artifact names are matched loosely (substring) to tolerate path prefixes.
- Missing `spec_text` → section checks are skipped, not failed.

## Files
See [DOCS.md](DOCS.md). Rules live in `governance_rules/`, report layout in `audit_templates/`.
