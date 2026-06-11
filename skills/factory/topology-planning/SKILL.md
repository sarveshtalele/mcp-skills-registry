---
name: topology-planning
version: 1.0.0
description: >
  Generate a target architecture and migration plan from a discovery summary. Produces a
  migration_plan.md with target topology, ADRs, phased strategy, and risks. Trigger on: target
  architecture, migration plan, topology, modernization plan.
author: sarveshtalele
license: MIT
category: modernization
tags: [modernization, architecture, migration, planning]
execution:
  type: python-script
  entrypoint: scripts/main.py:run
  timeout_seconds: 20
inputs:
  - name: discovery_summary
    type: string
    required: true
    description: Summary from legacy-discovery.
  - name: target_style
    type: string
    required: false
    default: "microservices"
    description: Target architecture style.
outputs:
  - name: migration_plan_markdown
    type: string
    description: The migration plan.
  - name: phases
    type: array
    description: Ordered migration phases.
status: active
---

# topology-planning

Generate a target architecture and migration plan from a discovery summary. Produces a migration_plan.md with target topology, ADRs, phased strategy, and risks. Trigger on: target architecture, migration plan, topology, modernization plan.
