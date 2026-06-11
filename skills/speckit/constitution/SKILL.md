---
name: speckit-constitution
version: 1.0.0
description: >
  Generate a project constitution for spec-driven development: the guiding
  principles, quality bars, and constraints every later artifact must respect.
  Trigger on: project constitution, engineering principles, ground rules, SDD setup.
author: sarveshtalele
license: MIT
category: sdd
tags: [sdd, spec-kit, governance, constitution]
execution:
  type: python-script
  entrypoint: scripts/main.py:run
  timeout_seconds: 15
inputs:
  - name: project_name
    type: string
    required: true
    description: Name of the project or product.
  - name: principles
    type: array
    items: string
    required: false
    description: Optional list of guiding principles to include.
outputs:
  - name: constitution_markdown
    type: string
    description: A ready-to-commit constitution.md.
status: active
---

# speckit-constitution

Produces `constitution.md` — the non-negotiable principles for the project. Run
this first; later SDD steps (specify, plan, tasks) should honour it.
