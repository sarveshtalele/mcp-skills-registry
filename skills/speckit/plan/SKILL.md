---
name: speckit-plan
version: 1.0.0
description: >
  Turn an approved specification into a technical plan (plan.md): architecture,
  components, data model, key decisions, and milestones. Trigger on: create a
  plan, technical plan, implementation plan, SDD plan, design from spec.
author: sarveshtalele
license: MIT
category: sdd
tags: [sdd, spec-kit, architecture, planning]
execution:
  type: python-script
  entrypoint: scripts/main.py:run
  timeout_seconds: 15
inputs:
  - name: spec_summary
    type: string
    required: true
    description: Summary of the approved specification.
  - name: tech_stack
    type: array
    items: string
    required: false
    description: Optional preferred technologies.
outputs:
  - name: plan_markdown
    type: string
    description: A structured plan.md skeleton.
status: active
---

# speckit-plan

Converts a spec summary into a `plan.md`. Then run `speckit-tasks` to break it
into an executable backlog.
