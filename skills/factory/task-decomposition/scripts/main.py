"""task-decomposition — convert a specification into a tasks.yaml backlog."""

from __future__ import annotations

_TASK_TEMPLATES = [
    ("design", "Design the interface/contract", 3),
    ("implement", "Implement the capability", 5),
    ("test", "Add unit + integration tests", 3),
]


def _yaml_escape(text: str) -> str:
    return text.replace('"', '\\"')


def run(inputs: dict) -> dict:
    summary = inputs["spec_summary"].strip()
    n = int(inputs.get("num_stories") or 3)
    n = max(1, min(n, 12))

    lines = [f'# Backlog derived from: "{_yaml_escape(summary)}"', "stories:"]
    tid = 1
    for s in range(1, n + 1):
        sid = f"S{s:02d}"
        lines.append(f"  - id: {sid}")
        lines.append(f'    title: "Story {s} — <capability>"')
        lines.append('    as_a: "<user>"')
        lines.append('    i_want: "<capability>"')
        lines.append('    so_that: "<benefit>"')
        lines.append("    tasks:")
        prev = None
        for kind, desc, est in _TASK_TEMPLATES:
            ident = f"T{tid:03d}"
            lines.append(f"      - id: {ident}")
            lines.append(f"        type: {kind}")
            lines.append(f'        summary: "{desc}"')
            lines.append(f"        estimate_points: {est}")
            lines.append(f"        depends_on: {('[' + prev + ']') if prev else '[]'}")
            lines.append('        acceptance: "given <precondition>, when <action>, then <result>"')
            prev = ident
            tid += 1
    yaml_text = "\n".join(lines) + "\n"
    return {"tasks_yaml": yaml_text, "story_count": n, "task_count": tid - 1}
