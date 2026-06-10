"""Standalone subprocess harness that executes a single skill entrypoint.

Invoked as::

    python _runner.py <script_path> <callable_name>

Reads a JSON ``inputs`` object from stdin and writes a JSON envelope to stdout:
``{"output": {...}}`` on success or ``{"error": "..."}`` on failure.

This file intentionally has **no** dependency on the ``skill_registry`` package so
it can run in a clean subprocess with only the skill's own directory importable.
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import sys
import traceback
from pathlib import Path


def _load_callable(script_path: Path, callable_name: str):
    spec = importlib.util.spec_from_file_location("_skill_entrypoint", script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load module from {script_path}")
    module = importlib.util.module_from_spec(spec)
    # Make sibling files in the skill importable (e.g. scripts/engine/*).
    sys.path.insert(0, str(script_path.parent))
    spec.loader.exec_module(module)
    if not hasattr(module, callable_name):
        raise AttributeError(f"entrypoint '{callable_name}' not found in {script_path.name}")
    return getattr(module, callable_name)


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({"error": "usage: _runner.py <script_path> <callable>"}))
        return 2

    script_path = Path(sys.argv[1]).resolve()
    callable_name = sys.argv[2]

    try:
        inputs = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": f"invalid input JSON: {exc}"}))
        return 1

    # Reserve real stdout for the JSON envelope; send any skill print()/import
    # chatter to stderr so it cannot corrupt the result the parent parses.
    real_stdout = sys.stdout
    try:
        with contextlib.redirect_stdout(sys.stderr):
            entry = _load_callable(script_path, callable_name)
            result = entry(inputs)
            if not isinstance(result, dict):
                raise TypeError(f"skill must return a dict, got {type(result).__name__}")
        print(json.dumps({"output": result}), file=real_stdout)
        return 0
    except Exception as exc:  # noqa: BLE001 - report any skill failure to the parent
        detail = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        print(json.dumps({"error": detail}), file=real_stdout)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
