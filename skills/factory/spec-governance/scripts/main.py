"""spec-governance — validate artifacts against governance rules; emit an audit."""

from __future__ import annotations

# Required artifacts and their weight toward the compliance score.
_REQUIRED_ARTIFACTS = {
    "spec.md": 20,
    "plan.md": 15,
    "tasks.yaml": 10,
    "tests": 25,
    "architecture.md": 15,
    "adr": 15,
}
# Sections a spec should contain (checked if spec_text supplied).
_REQUIRED_SECTIONS = ["overview", "requirements", "acceptance", "out of scope"]
_PASS_THRESHOLD = 70


def run(inputs: dict) -> dict:
    present = inputs["artifacts_present"]
    if isinstance(present, str):
        present = [present]
    present_norm = {p.strip().lower() for p in present}
    spec_text = (inputs.get("spec_text") or "").lower()

    score = 0
    artifact_rows = []
    for name, weight in _REQUIRED_ARTIFACTS.items():
        ok = any(name.lower() in p or p in name.lower() for p in present_norm)
        score += weight if ok else 0
        artifact_rows.append(f"| `{name}` | {'✅' if ok else '❌'} | {weight} |")

    section_rows = []
    if spec_text:
        for sec in _REQUIRED_SECTIONS:
            ok = sec in spec_text
            section_rows.append(f"| {sec} | {'✅' if ok else '❌'} |")

    score = min(score, 100)
    passed = score >= _PASS_THRESHOLD

    sections_block = ""
    if section_rows:
        sections_block = (
            "\n## Spec section checks\n"
            "| Section | Present |\n|---------|---------|\n" + "\n".join(section_rows) + "\n"
        )

    md = f"""# Governance Audit

**Result:** {'✅ PASS' if passed else '❌ FAIL'} &nbsp; **Score:** {score}/100 (threshold {_PASS_THRESHOLD})

## Required artifacts
| Artifact | Present | Weight |
|----------|---------|--------|
{chr(10).join(artifact_rows)}
{sections_block}
## Recommendation
{"Cleared for the next gate." if passed else "Address the ❌ items above before proceeding."}
"""
    return {"audit_markdown": md, "score": score, "passed": passed}
