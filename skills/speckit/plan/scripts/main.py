"""Generate a technical plan (plan.md) from a spec summary."""

from __future__ import annotations


def run(inputs: dict) -> dict:
    summary = inputs["spec_summary"].strip()
    stack = inputs.get("tech_stack") or ["<language>", "<framework>", "<datastore>"]
    stack_lines = "\n".join(f"- {t}" for t in stack)
    md = f"""# Technical Plan

## Spec summary
{summary}

## Proposed stack
{stack_lines}

## Architecture
- Describe the high-level components and how they interact.
- Include a diagram reference (e.g. docs/architecture.md).

## Components
| Component | Responsibility | Depends on |
|-----------|----------------|-----------|
| ... | ... | ... |

## Data model
- Entity: fields, relationships, constraints.

## Key decisions (ADRs)
- ADR-1: ... (context, decision, consequences)

## Milestones
1. M1 — walking skeleton
2. M2 — core features
3. M3 — hardening + release
"""
    return {"plan_markdown": md, "component_stack": list(stack)}
