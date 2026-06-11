---
name: speckit-specify
version: 1.0.0
description: >
  Turn a plain feature description into a structured specification (spec.md):
  overview, user stories, functional and non-functional requirements, and
  testable acceptance criteria. Trigger on: write a spec, specify this feature,
  create requirements, spec-driven development, SDD specify.
author: sarveshtalele
license: MIT
category: sdd
tags: [sdd, spec-kit, requirements, specification]
execution:
  type: python-script
  entrypoint: scripts/main.py:run
  timeout_seconds: 15
inputs:
  - name: feature_description
    type: string
    required: true
    description: Plain-language description of the feature or product.
  - name: feature_name
    type: string
    required: false
    description: Short slug/name for the feature.
outputs:
  - name: spec_markdown
    type: string
    description: A structured spec.md skeleton to refine.
status: active
---

# speckit-specify

Converts an idea into a reviewable `spec.md`. Fill the `[NEEDS CLARIFICATION]`
markers, then proceed to `speckit-plan`.
