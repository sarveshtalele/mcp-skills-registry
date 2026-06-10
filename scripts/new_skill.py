"""Scaffold a new skill by copying ``skills/_template`` and renaming it.

Usage::

    python scripts/new_skill.py my-new-skill
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SKILLS_DIR = _ROOT / "skills"
_TEMPLATE_DIR = _SKILLS_DIR / "_template"
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def create_skill(name: str) -> Path:
    """Create a new skill directory from the template. Returns its path."""
    if not _SLUG_RE.match(name):
        raise ValueError(f"'{name}' must be a lowercase slug (a-z, 0-9, hyphen)")

    target = _SKILLS_DIR / name
    if target.exists():
        raise FileExistsError(f"skill '{name}' already exists at {target}")
    if not _TEMPLATE_DIR.exists():
        raise FileNotFoundError(f"template not found at {_TEMPLATE_DIR}")

    shutil.copytree(_TEMPLATE_DIR, target)

    # Replace the placeholder name in SKILL.md.
    manifest = target / "SKILL.md"
    text = manifest.read_text(encoding="utf-8").replace("name: my-skill", f"name: {name}")
    manifest.write_text(text, encoding="utf-8")
    return target


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Scaffold a new skill.")
    parser.add_argument("name", help="skill name (lowercase slug)")
    args = parser.parse_args()

    try:
        path = create_skill(args.name)
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Created skill at {path.relative_to(_ROOT)}")
    print("Next: edit SKILL.md and scripts/main.py, then reload the registry.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
