"""Entrypoint for the skill.

Contract:
- Expose a ``run(inputs: dict) -> dict`` function.
- ``inputs`` are already validated against ``SKILL.md`` by the registry.
- Return a JSON-serializable dict matching the declared ``outputs``.
- Raise an exception to signal failure; the registry reports it to the caller.
"""

from __future__ import annotations


def run(inputs: dict) -> dict:
    """Implement the skill logic here."""
    example_input = inputs["example_input"]
    return {"example_output": f"received: {example_input}"}
