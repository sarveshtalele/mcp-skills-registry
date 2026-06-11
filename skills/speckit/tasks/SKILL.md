---
name: speckit-tasks
version: 1.0.0
description: >
  Break a technical plan into an ordered, testable task backlog (tasks.md) with
  IDs, dependencies, and acceptance checks. Trigger on: break into tasks, create
  backlog, task decomposition, SDD tasks, generate work items.
author: sarveshtalele
license: MIT
category: sdd
tags: [sdd, spec-kit, tasks, backlog, planning]
execution:
  type: python-script
  entrypoint: scripts/main.py:run
  timeout_seconds: 15
inputs:
  - name: plan_summary
    type: string
    required: true
    description: Summary of the technical plan to decompose.
  - name: num_phases
    type: integer
    required: false
    default: 3
    description: Number of delivery phases to scaffold.
outputs:
  - name: tasks_markdown
    type: string
    description: A structured tasks.md backlog.
status: active
---

# speckit-tasks

Decomposes a `plan.md` into an ordered backlog. Each task carries an ID,
dependencies, and an acceptance check so progress is verifiable.
