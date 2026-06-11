"""topology-planning — produce a target architecture + migration plan."""

from __future__ import annotations

_STYLES = {
    "microservices": [
        "Decompose by bounded context into independently deployable services.",
        "Introduce an API gateway and async messaging between services.",
        "One datastore per service; no shared databases.",
    ],
    "modular-monolith": [
        "Keep a single deployable but enforce module boundaries.",
        "Define explicit internal APIs between modules.",
        "Split the schema by module ownership.",
    ],
    "serverless": [
        "Map request flows to functions; externalise state.",
        "Use managed queues/streams for async work.",
        "Adopt infrastructure-as-code for every function.",
    ],
}


def run(inputs: dict) -> dict:
    summary = inputs["discovery_summary"].strip()
    style = (inputs.get("target_style") or "microservices").lower()
    principles = _STYLES.get(style, _STYLES["microservices"])

    phases = [
        {"id": "P1", "name": "Strangler scaffolding",
         "goal": "Stand up the new platform alongside the legacy app; route a thin slice."},
        {"id": "P2", "name": "Extract core domains",
         "goal": "Migrate highest-value bounded contexts behind the gateway."},
        {"id": "P3", "name": "Data migration",
         "goal": "Move data ownership per service; dual-write then cut over."},
        {"id": "P4", "name": "Decommission legacy",
         "goal": "Retire legacy paths once parity and metrics are verified."},
    ]
    principle_lines = "\n".join(f"- {p}" for p in principles)
    phase_lines = "\n".join(f"### {p['id']} — {p['name']}\n{p['goal']}\n" for p in phases)

    md = f"""# Migration Plan → {style}

## Discovery summary
{summary}

## Target architecture principles
{principle_lines}

## Architecture Decision Records
- **ADR-1:** Adopt the {style} style. _Context / decision / consequences._
- **ADR-2:** Strangler-fig migration over big-bang rewrite.
- **ADR-3:** Per-domain data ownership.

## Phased migration
{phase_lines}
## Risks & mitigations
| Risk | Mitigation |
|------|-----------|
| Data divergence during dual-write | Reconciliation jobs + checksums |
| Hidden legacy behaviour | Characterization tests before extraction |
| Team capacity | Sequence phases by value/risk |
"""
    return {"migration_plan_markdown": md, "phases": phases}
