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

Turn a discovery summary into a target architecture and a phased, low-risk
migration plan with ADRs.

## When to use
After `legacy-discovery`, when defining the target state. Triggers: *target
architecture, migration plan, topology, modernization plan*.

## Inputs
- `discovery_summary` (string, required) — summary of the current system.
- `target_style` (string, optional) — `microservices` | `modular-monolith` | `serverless`.

## Outputs
- `migration_plan_markdown` — principles, ADRs, phased plan, risk table.
- `phases` — ordered phase objects `{id, name, goal}`.

## How it works
Selects a principle set for the chosen style and assembles a strangler-fig
migration across four phases with a risk/mitigation table.

## User stories
- *As an architect*, I get a defensible target architecture and an incremental
  path, not a big-bang rewrite.

## Edge cases
- Unknown `target_style` → defaults to `microservices`.
- Empty summary → plan still renders with prompts to fill in.

## Files
See [DOCS.md](DOCS.md).
