"""Generate an ordered task backlog (tasks.md) from a plan summary."""

from __future__ import annotations


def run(inputs: dict) -> dict:
    summary = inputs["plan_summary"].strip()
    phases = int(inputs.get("num_phases") or 3)
    phases = max(1, min(phases, 8))
    lines = ["# Task Backlog", "", f"_Derived from:_ {summary}", ""]
    tid = 1
    task_ids = []
    for phase in range(1, phases + 1):
        lines.append(f"## Phase {phase}")
        for _ in range(3):
            ident = f"T{tid:03d}"
            task_ids.append(ident)
            dep = f"depends: T{tid-1:03d}" if tid > 1 else "depends: none"
            lines.append(f"- [ ] **{ident}** — <task summary> ({dep})")
            lines.append(f"      - acceptance: given ..., when ..., then ...")
            tid += 1
        lines.append("")
    md = "\n".join(lines)
    return {"tasks_markdown": md, "task_ids": task_ids, "phase_count": phases}
