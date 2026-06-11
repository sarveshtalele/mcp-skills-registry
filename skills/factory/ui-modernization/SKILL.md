---
name: ui-modernization
version: 1.0.0
description: >
  Plan migration of a legacy UI to a modern React component architecture. Produces a component
  inventory, a target component tree, and starter React + test stubs. Trigger on: modernize
  UI, convert to React, UI migration, frontend modernization.
author: sarveshtalele
license: MIT
category: frontend
tags: [frontend, react, ui, modernization]
execution:
  type: python-script
  entrypoint: scripts/main.py:run
  timeout_seconds: 20
inputs:
  - name: screens
    type: array
    items: string
    required: true
    description: List of legacy screen/page names.
  - name: framework
    type: string
    required: false
    default: "react"
    description: Target framework.
outputs:
  - name: plan_markdown
    type: string
    description: UI modernization plan.
  - name: components
    type: array
    description: Proposed component list.
  - name: sample_component
    type: string
    description: Starter component stub.
status: active
---

# ui-modernization

Plan migration of a legacy UI to a modern React component architecture. Produces a component inventory, a target component tree, and starter React + test stubs. Trigger on: modernize UI, convert to React, UI migration, frontend modernization.
