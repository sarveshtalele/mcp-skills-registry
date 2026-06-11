---
name: task-decomposition
version: 1.0.0
description: >
  Convert a specification into a structured, dependency-ordered backlog as tasks.yaml with
  stories, tasks, estimates, and acceptance checks. Trigger on: decompose tasks, create
  backlog, convert spec to tasks, planning, work items.
author: sarveshtalele
license: MIT
category: planning
tags: [planning, backlog, tasks, jira]
execution:
  type: python-script
  entrypoint: scripts/main.py:run
  timeout_seconds: 20
inputs:
  - name: spec_summary
    type: string
    required: true
    description: Specification summary to decompose.
  - name: num_stories
    type: integer
    required: false
    default: 3
    description: Number of stories to scaffold.
outputs:
  - name: tasks_yaml
    type: string
    description: Backlog as YAML.
  - name: story_count
    type: integer
    description: Number of stories produced.
status: active
---

# task-decomposition

Convert a specification summary into a dependency-ordered backlog (`tasks.yaml`)
with stories, tasks, estimates, and acceptance checks.

## When to use
After a spec/plan is approved. Triggers: *decompose tasks, create backlog,
convert spec to tasks, work items*.

## Inputs
- `spec_summary` (string, required).
- `num_stories` (integer, optional, default 3, clamped 1–12).

## Outputs
- `tasks_yaml` — YAML backlog.
- `story_count`, `task_count`.

## How it works
For each story it scaffolds design → implement → test tasks with linear
dependencies and acceptance placeholders, emitting valid YAML.

## User stories
- *As a delivery lead*, I turn a spec into a structured backlog ready for Jira
  import (see `jira_templates/`).

## Edge cases
- `num_stories` out of range → clamped.
- Quotes in the summary → escaped so the YAML stays valid.

## Files
See [DOCS.md](DOCS.md).
