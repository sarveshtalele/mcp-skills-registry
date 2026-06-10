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
import os
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

    # The JSON envelope must be the ONLY thing on stdout. Skills (and their
    # subprocesses, e.g. `git clone`) may write to stdout — at the Python level
    # AND directly to file descriptor 1 — which would corrupt the envelope.
    # Redirect fd 1 to fd 2 (stderr) for the duration of execution, then restore
    # it and emit the envelope. This captures subprocess output too.
    saved_stdout_fd = os.dup(1)
    try:
        sys.stdout.flush()
        os.dup2(2, 1)  # point fd 1 at stderr
        with contextlib.redirect_stdout(sys.stderr):
            entry = _load_callable(script_path, callable_name)
            result = entry(inputs)
        if not isinstance(result, dict):
            raise TypeError(f"skill must return a dict, got {type(result).__name__}")
        envelope = {"output": result}
        rc = 0
    except Exception as exc:  # noqa: BLE001 - report any skill failure to the parent
        detail = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        envelope = {"error": detail}
        rc = 1
    finally:
        sys.stderr.flush()
        os.dup2(saved_stdout_fd, 1)  # restore real stdout
        os.close(saved_stdout_fd)

    os.write(1, (json.dumps(envelope) + "\n").encode("utf-8"))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
