"""
API Contract Validator
Scans the repository for OpenAPI / Swagger specs and GraphQL schemas.
Detects deprecated endpoints, removed fields, and version-major bumps
that signal breaking changes.  Relies only on the *current* state of the
repo; a git-diff-based breaking-change detector is a natural extension.
"""
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False


_OPENAPI_NAMES = {
    "openapi.json", "openapi.yaml", "openapi.yml",
    "swagger.json", "swagger.yaml", "swagger.yml",
    "api-spec.json", "api-spec.yaml", "api-spec.yml",
    "api.yaml", "api.json",
}

_IGNORE_DIRS = {"node_modules", ".git", "dist", "build", "__pycache__", "vendor"}


class ContractValidator:
    def __init__(self, repo_path: Path, base_branch: str = "main") -> None:
        self.repo_path = repo_path
        self.base_branch = base_branch

    def validate(self) -> List[Dict[str, Any]]:
        openapi, graphql, proto = self._discover_all()
        violations: List[Dict[str, Any]] = []
        for p in openapi:
            violations.extend(self._validate_openapi(p))
        for p in graphql:
            violations.extend(self._validate_graphql(p))
        for p in proto:
            violations.extend(self._validate_protobuf(p))
        return violations

    # ------------------------------------------------------------------
    # Single-pass discovery — walks the tree exactly once
    # ------------------------------------------------------------------

    def _discover_all(self):
        openapi: List[Path] = []
        graphql: List[Path] = []
        proto: List[Path] = []

        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in _IGNORE_DIRS]
            for name in files:
                lower = name.lower()
                p = Path(root) / name

                if lower in _OPENAPI_NAMES:
                    openapi.append(p)
                elif lower.endswith((".yaml", ".yml", ".json")):
                    try:
                        snippet = p.read_text(encoding="utf-8", errors="ignore")[:400]
                        if re.search(r'"?openapi"?\s*:', snippet) or re.search(r'"?swagger"?\s*:', snippet):
                            openapi.append(p)
                    except OSError:
                        pass
                elif name.endswith((".graphql", ".gql")):
                    graphql.append(p)
                elif name.endswith(".proto"):
                    proto.append(p)

        return openapi, graphql, proto

    # ------------------------------------------------------------------
    # OpenAPI validation
    # ------------------------------------------------------------------

    def _validate_openapi(self, spec_path: Path) -> List[Dict[str, Any]]:
        violations: List[Dict[str, Any]] = []
        rel = self._rel(spec_path)

        try:
            raw = spec_path.read_text(encoding="utf-8")
            spec = self._parse_spec(raw, spec_path.suffix)
        except Exception as exc:
            return [self._violation("parse_error", "warning", str(spec_path), f"Cannot parse: {exc}", rel)]

        if not isinstance(spec, dict):
            return violations

        # Version-major bump → potential breaking change
        info = spec.get("info", {})
        version_str = str(info.get("version", "0.0.0"))
        major = version_str.split(".")[0]
        if major.isdigit() and int(major) > 1:
            violations.append(self._violation(
                "major_version", "warning",
                f"Version {version_str}",
                "Major version > 1 may indicate breaking API changes",
                rel,
            ))

        # Per-endpoint checks
        for endpoint, methods in spec.get("paths", {}).items():
            if not isinstance(methods, dict):
                continue
            for method, definition in methods.items():
                if not isinstance(definition, dict):
                    continue
                label = f"{method.upper()} {endpoint}"

                if definition.get("deprecated", False):
                    violations.append(self._violation(
                        "deprecated_endpoint", "warning", label,
                        "Endpoint is marked deprecated — consumers must migrate", rel,
                    ))

                # Check for removed required parameters (simplified heuristic)
                for param in definition.get("parameters", []):
                    if isinstance(param, dict) and param.get("required") and not param.get("schema"):
                        violations.append(self._violation(
                            "missing_param_schema", "warning", label,
                            f"Required parameter '{param.get('name', '?')}' has no schema definition", rel,
                        ))

        return violations

    def _parse_spec(self, raw: str, suffix: str) -> Any:
        if suffix in (".yaml", ".yml"):
            if _YAML_AVAILABLE:
                return yaml.safe_load(raw)
            # Best-effort JSON fallback for YAML that happens to be valid JSON
        return json.loads(raw)

    # ------------------------------------------------------------------
    # GraphQL validation
    # ------------------------------------------------------------------

    def _validate_graphql(self, schema_path: Path) -> List[Dict[str, Any]]:
        violations: List[Dict[str, Any]] = []
        rel = self._rel(schema_path)

        try:
            content = schema_path.read_text(encoding="utf-8")
        except OSError:
            return violations

        # @deprecated directive
        for m in re.finditer(
            r'(\w+)[^@\n]*@deprecated(?:\s*\(reason:\s*"([^"]*)")?\s*',
            content,
        ):
            field_name = m.group(1)
            reason = m.group(2) or "No reason given"
            violations.append(self._violation(
                "deprecated_graphql_field", "warning",
                f"GraphQL field: {field_name}",
                f"Deprecated — {reason}", rel,
            ))

        # Removed / non-null fields without defaults are potential breaking changes
        for m in re.finditer(r'(\w+)\s*:\s*(\w+!)', content):
            field_name = m.group(1)
            field_type = m.group(2)
            if field_name.lower() in ("id", "createdAt", "updatedAt"):
                continue  # expected non-null
            violations.append(self._violation(
                "non_null_field", "info",
                f"GraphQL field: {field_name}",
                f"Non-null type '{field_type}' — adding new non-null fields is a breaking change for existing clients",
                rel,
            ))

        return violations

    # ------------------------------------------------------------------
    # Protobuf validation
    # ------------------------------------------------------------------

    def _validate_protobuf(self, proto_path: Path) -> List[Dict[str, Any]]:
        violations: List[Dict[str, Any]] = []
        rel = self._rel(proto_path)

        try:
            content = proto_path.read_text(encoding="utf-8")
        except OSError:
            return violations

        # Reserved field numbers or names not covered signal risk
        if "reserved" not in content:
            violations.append(self._violation(
                "missing_reserved_fields", "warning",
                proto_path.name,
                "No 'reserved' declarations found — removing fields without reserving numbers is a breaking change",
                rel,
            ))

        # Deprecated option
        for m in re.finditer(r'(\w+)\s*=\s*\d+\s*\[deprecated\s*=\s*true\]', content):
            violations.append(self._violation(
                "deprecated_proto_field", "warning",
                f"Protobuf field: {m.group(1)}",
                "Field marked deprecated", rel,
            ))

        return violations

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _rel(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.repo_path)).replace("\\", "/")
        except ValueError:
            return str(path)

    @staticmethod
    def _violation(
        vtype: str, severity: str, endpoint: str, detail: str, spec_file: str
    ) -> Dict[str, Any]:
        return {
            "type": vtype,
            "severity": severity,
            "endpoint": endpoint,
            "detail": detail,
            "spec_file": spec_file,
        }
