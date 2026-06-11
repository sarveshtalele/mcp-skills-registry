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

Convert a specification into a structured, dependency-ordered backlog as tasks.yaml with stories, tasks, estimates, and acceptance checks. Trigger on: decompose tasks, create backlog, convert spec to tasks, planning, work items.
