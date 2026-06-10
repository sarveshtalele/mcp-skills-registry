"""
Ownership Parser
Reads CODEOWNERS, package.json, and pyproject.toml to build a file-to-owner
mapping.  Returns an OwnershipMap whose get_owners() method returns the list
of owners for any repository-relative file path.

CODEOWNERS semantics: the LAST matching rule wins (same as GitHub's behaviour).
"""
import fnmatch
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple


class OwnershipMap:
    """Holds ordered (pattern, owners) rules and resolves ownership on demand."""

    def __init__(self, rules: List[Tuple[str, List[str]]]) -> None:
        self._rules = rules  # ordered; last match wins

    def get_owners(self, file_path: str) -> List[str]:
        matched: List[str] = []
        normalised = file_path.replace("\\", "/").lstrip("/")
        for pattern, owners in self._rules:
            if self._matches(pattern, normalised):
                matched = owners
        return matched

    def all_owners(self) -> List[str]:
        seen: List[str] = []
        for _, owners in self._rules:
            for o in owners:
                if o not in seen:
                    seen.append(o)
        return seen

    @staticmethod
    def _matches(pattern: str, path: str) -> bool:
        pattern = pattern.lstrip("/")
        if not pattern:
            return False
        # Directory pattern (ends with /)
        if pattern.endswith("/"):
            norm = pattern.rstrip("/")
            return path.startswith(pattern) or f"/{norm}/" in f"/{path}/"
        # Direct glob match against full path
        if fnmatch.fnmatch(path, pattern):
            return True
        # Basename match for simple (no-slash) patterns like "*.py" or "Makefile"
        if "/" not in pattern and fnmatch.fnmatch(path.split("/")[-1], pattern):
            return True
        # Subpath match: "src/*.py" should match "app/src/foo.py"
        # Walk every suffix of the path and test the pattern against it
        parts = path.split("/")
        for i in range(len(parts)):
            if fnmatch.fnmatch("/".join(parts[i:]), pattern):
                return True
        return False


class OwnershipParser:
    _CODEOWNERS_LOCATIONS = [
        ".github/CODEOWNERS",
        "CODEOWNERS",
        "docs/CODEOWNERS",
    ]

    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path

    def parse(self) -> OwnershipMap:
        rules: List[Tuple[str, List[str]]] = []

        # 1. CODEOWNERS (highest specificity)
        for loc in self._CODEOWNERS_LOCATIONS:
            full = self.repo_path / loc
            if full.exists():
                rules.extend(self._parse_codeowners(full))
                break

        # 2. package.json maintainers (fallback, covers entire repo)
        pkg = self.repo_path / "package.json"
        if pkg.exists():
            rules.extend(self._parse_package_json(pkg))

        # 3. pyproject.toml authors
        pyproject = self.repo_path / "pyproject.toml"
        if pyproject.exists():
            rules.extend(self._parse_pyproject(pyproject))

        return OwnershipMap(rules)

    # ------------------------------------------------------------------
    # Parsers
    # ------------------------------------------------------------------

    def _parse_codeowners(self, path: Path) -> List[Tuple[str, List[str]]]:
        rules: List[Tuple[str, List[str]]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                pattern = parts[0].lstrip("/")
                owners = parts[1:]
                rules.append((pattern, owners))
        return rules

    def _parse_package_json(self, path: Path) -> List[Tuple[str, List[str]]]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

        maintainers = data.get("maintainers", data.get("author", []))
        if isinstance(maintainers, str):
            maintainers = [maintainers]
        if isinstance(maintainers, dict):
            maintainers = [maintainers.get("name", maintainers.get("email", ""))]

        names = []
        for m in maintainers:
            if isinstance(m, dict):
                names.append(m.get("name") or m.get("email") or "")
            elif isinstance(m, str):
                names.append(m)

        names = [n for n in names if n]
        if names:
            return [("*", names)]
        return []

    def _parse_pyproject(self, path: Path) -> List[Tuple[str, List[str]]]:
        content = path.read_text(encoding="utf-8")
        # Simple regex extraction — avoids a toml dependency
        authors: List[str] = []
        for m in re.finditer(r'authors\s*=\s*\[(.*?)\]', content, re.DOTALL):
            for name_m in re.finditer(r'"([^"]+)"', m.group(1)):
                authors.append(name_m.group(1))
        if authors:
            return [("*", authors)]
        return []
