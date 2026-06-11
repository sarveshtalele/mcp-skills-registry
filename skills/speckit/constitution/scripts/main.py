"""Generate a project constitution for spec-driven development."""

from __future__ import annotations

_DEFAULT_PRINCIPLES = [
    "Specifications precede code; no implementation without an approved spec.",
    "Every change is traceable to a requirement and an acceptance criterion.",
    "Prefer simple, well-tested solutions over clever ones.",
    "Security and accessibility are requirements, not afterthoughts.",
    "Document decisions as ADRs; revisit them when assumptions change.",
]


def run(inputs: dict) -> dict:
    name = inputs["project_name"]
    principles = inputs.get("principles") or _DEFAULT_PRINCIPLES
    lines = [f"# {name} — Engineering Constitution", ""]
    lines.append("These principles govern every specification, plan, and task.\n")
    for i, p in enumerate(principles, 1):
        lines.append(f"{i}. {p}")
    lines += ["", "## Amendment process", "",
              "Changes require a short ADR and review by a maintainer."]
    md = "\n".join(lines) + "\n"
    return {"constitution_markdown": md, "principle_count": len(principles)}
