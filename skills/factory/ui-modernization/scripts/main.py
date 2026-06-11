"""ui-modernization — plan a legacy UI migration to a modern component framework."""

from __future__ import annotations

import re


def _component_name(screen: str) -> str:
    parts = re.split(r"[^A-Za-z0-9]+", screen.strip())
    name = "".join(p.capitalize() for p in parts if p) or "Screen"
    return name if name.endswith(("Page", "View", "Screen")) else name + "Page"


def _sample_component(name: str) -> str:
    return (
        f"export default function {name}() {{\n"
        f"  // TODO: port legacy markup + behaviour\n"
        f"  return (\n"
        f"    <main className=\"{name.lower()}\">\n"
        f"      <h1>{name}</h1>\n"
        f"    </main>\n"
        f"  );\n"
        f"}}\n"
    )


def run(inputs: dict) -> dict:
    screens = inputs["screens"]
    if isinstance(screens, str):
        screens = [screens]
    if not screens:
        raise ValueError("provide at least one screen name")
    framework = (inputs.get("framework") or "react").lower()

    components = [_component_name(s) for s in screens]
    rows = "\n".join(f"| {s} | `{c}` | `components/{c}.tsx` |" for s, c in zip(screens, components))
    sample = _sample_component(components[0])

    md = f"""# UI Modernization Plan ({framework})

## Component inventory
| Legacy screen | Component | Path |
|---------------|-----------|------|
{rows}

## Target component tree
- `App`
  - `Layout` (nav, shell)
{chr(10).join(f"    - `{c}`" for c in components)}

## Approach
1. Establish the {framework} app shell, routing, and design tokens.
2. Port screens one at a time behind a feature flag (strangler).
3. Co-locate a test per component; snapshot + interaction tests.
4. Replace legacy routes once parity is verified.

## Definition of done (per screen)
- [ ] Visual + behavioural parity
- [ ] Accessibility (keyboard, ARIA) checked
- [ ] Unit + interaction tests passing
"""
    return {"plan_markdown": md, "components": components, "sample_component": sample}
