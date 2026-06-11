"""test-generation — produce a test strategy and starter stubs for modules."""

from __future__ import annotations

_DEFAULT_FRAMEWORKS = ["pytest", "jest", "playwright"]


def _pytest_stub(module: str) -> str:
    fn = module.replace("-", "_").replace("/", "_")
    return (
        f"def test_{fn}_happy_path():\n"
        f"    # arrange / act / assert\n"
        f"    assert True  # TODO: cover {module}\n"
    )


def _jest_stub(module: str) -> str:
    return (
        f"describe('{module}', () => {{\n"
        f"  it('works', () => {{\n"
        f"    expect(true).toBe(true); // TODO\n"
        f"  }});\n"
        f"}});\n"
    )


def _playwright_stub(module: str) -> str:
    return (
        f"import {{ test, expect }} from '@playwright/test';\n\n"
        f"test('{module} e2e', async ({{ page }}) => {{\n"
        f"  await page.goto('/');\n"
        f"  // TODO: drive {module}\n"
        f"}});\n"
    )


def run(inputs: dict) -> dict:
    modules = inputs["modules"]
    if isinstance(modules, str):
        modules = [modules]
    if not modules:
        raise ValueError("provide at least one module")
    frameworks = inputs.get("frameworks") or _DEFAULT_FRAMEWORKS

    matrix = "\n".join(
        f"| {m} | unit | integration | e2e |" for m in modules
    )
    md = f"""# Test Strategy

## Scope
Modules under test: {", ".join(f"`{m}`" for m in modules)}

## Pyramid
- **Unit** — fast, isolated, majority of coverage.
- **Integration** — module boundaries, data access, contracts.
- **E2E** — critical user journeys only.

## Coverage matrix
| Module | Unit | Integration | E2E |
|--------|------|-------------|-----|
{matrix}

## Frameworks
{", ".join(f"`{f}`" for f in frameworks)}

## Targets
- Line coverage ≥ 80% on changed code.
- Every bug fix ships with a regression test.
"""
    stubs: dict[str, dict[str, str]] = {}
    for m in modules:
        entry: dict[str, str] = {}
        if "pytest" in frameworks:
            entry["pytest"] = _pytest_stub(m)
        if "jest" in frameworks:
            entry["jest"] = _jest_stub(m)
        if "playwright" in frameworks:
            entry["playwright"] = _playwright_stub(m)
        stubs[m] = entry
    return {"test_plan_markdown": md, "stubs": stubs}
