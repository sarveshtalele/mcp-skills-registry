"""Generate a structured specification (spec.md) from a feature description."""

from __future__ import annotations

import re


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:40] or "feature"


def run(inputs: dict) -> dict:
    desc = inputs["feature_description"].strip()
    name = inputs.get("feature_name") or _slug(desc.split(".")[0])
    md = f"""# Specification: {name}

## Overview
{desc}

## User stories
- As a [user], I want [capability] so that [benefit]. _[NEEDS CLARIFICATION]_

## Functional requirements
- FR-1: The system SHALL ... _[NEEDS CLARIFICATION]_
- FR-2: The system SHALL ...

## Non-functional requirements
- NFR-1 (Performance): ...
- NFR-2 (Security): ...
- NFR-3 (Accessibility): ...

## Acceptance criteria
- [ ] Given ..., when ..., then ...
- [ ] Given ..., when ..., then ...

## Out of scope
- ...
"""
    markers = md.count("[NEEDS CLARIFICATION]")
    return {"spec_markdown": md, "feature_name": name, "open_questions": markers}
