"""Smoke test for the legacy-discovery skill entrypoint."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from main import run  # noqa: E402


def test_run_returns_dict():
    result = run(json.loads('{"repo_path": "."}'))
    assert isinstance(result, dict) and result
