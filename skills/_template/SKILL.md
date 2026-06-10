---
name: my-skill
version: 0.1.0
description: >
  One or two sentences describing what the skill does, followed by trigger phrases
  the agent should recognize. Trigger when the user says: ...
author: your-handle
license: MIT
category: general
tags: [example]
execution:
  type: python-script
  entrypoint: scripts/main.py:run
  timeout_seconds: 30
inputs:
  - name: example_input
    type: string
    required: true
    description: Describe this input.
outputs:
  - name: example_output
    type: string
    description: Describe this output.
status: active
---

# My Skill

Describe the skill and how the agent should use it.

## Steps

1. Step one.
2. Step two.

## Notes

Anything callers should know.
