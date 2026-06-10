"""
Impact Analyzer
Given a dependency graph and a list of changed files, performs a reverse-BFS
to find all directly and transitively affected modules, then categorises each
by type (api_endpoint, service, test, database, config, ui_component, library).
"""
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Set

from .graph_builder import DependencyGraph
from .ownership_parser import OwnershipMap


@dataclass
class ImpactedModule:
    path: str
    module_type: str
    change_proximity: str          # "direct" | "transitive"
    owners: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)


_API_CONTENT_PATTERNS = [
    re.compile(r'@(Get|Post|Put|Delete|Patch)Mapping', re.IGNORECASE),   # Spring
    re.compile(r'@app\.(get|post|put|delete|patch)\s*\('),               # Flask / FastAPI
    re.compile(r'router\.(get|post|put|delete|patch)\s*\('),             # Express
    re.compile(r'\[(HttpGet|HttpPost|HttpPut|HttpDelete|HttpPatch)\]'),   # ASP.NET
    re.compile(r'func\s+\w+.*http\.ResponseWriter'),                     # Go net/http
    re.compile(r'@(RestController|Controller|RequestMapping)', re.IGNORECASE),
]

_TEST_PATH_PATTERNS = [
    re.compile(r'(^|/)test(s)?/', re.IGNORECASE),
    re.compile(r'(^|/)__tests__/'),
    re.compile(r'\.test\.(js|ts|jsx|tsx|py)$'),
    re.compile(r'\.spec\.(js|ts|jsx|tsx|py)$'),
    re.compile(r'(^|/)test_[\w]+\.py$'),
    re.compile(r'[\w]+_test\.(go|py)$'),
]

_DB_PATH_PATTERNS = [
    re.compile(r'migration', re.IGNORECASE),
    re.compile(r'\.(sql)$', re.IGNORECASE),
    re.compile(r'(^|/)models?/', re.IGNORECASE),
    re.compile(r'(^|/)entities?/', re.IGNORECASE),
    re.compile(r'(^|/)schema\.', re.IGNORECASE),
    re.compile(r'(^|/)repository/', re.IGNORECASE),
]

_CONFIG_PATH_PATTERNS = [
    re.compile(r'(config|settings|appsettings|application)\.(py|js|ts|json|yaml|yml|xml|ini|env)$', re.IGNORECASE),
    re.compile(r'(^|/)config(s)?/', re.IGNORECASE),
    re.compile(r'\.env(\..*)?$'),
    re.compile(r'Dockerfile', re.IGNORECASE),
    re.compile(r'docker-compose', re.IGNORECASE),
    re.compile(r'(^|/)k8s/', re.IGNORECASE),
    re.compile(r'helm/', re.IGNORECASE),
]

_UI_PATH_PATTERNS = [
    re.compile(r'\.(jsx|tsx|vue|svelte)$'),
    re.compile(r'(^|/)components?/', re.IGNORECASE),
    re.compile(r'(^|/)pages?/', re.IGNORECASE),
    re.compile(r'(^|/)views?/', re.IGNORECASE),
]


class ImpactAnalyzer:
    def __init__(self, graph: DependencyGraph, ownership: OwnershipMap, repo_path: Path) -> None:
        self.graph = graph
        self.ownership = ownership
        self.repo_path = repo_path

    def analyze(self, changed_files: List[str]) -> Dict[str, Any]:
        normalized = [self._normalize(f) for f in changed_files]

        direct: Set[str] = set(normalized)
        transitive: Set[str] = set()
        for f in normalized:
            transitive.update(self.graph.get_reverse_deps(f, transitive=True))
        transitive -= direct

        impacted_modules: List[ImpactedModule] = []
        impacted_apis: List[Dict] = []
        regression_areas: List[str] = []
        required_tests: Set[str] = set()
        consumer_apps: Set[str] = set()

        for path in sorted(direct):
            m = self._classify(path, "direct")
            impacted_modules.append(m)
            self._collect_outputs(m, impacted_apis, regression_areas, required_tests, consumer_apps)

        for path in sorted(transitive):
            m = self._classify(path, "transitive")
            impacted_modules.append(m)
            self._collect_outputs(m, impacted_apis, regression_areas, required_tests, consumer_apps)

        return {
            "changed_files": normalized,
            "impacted_modules": [vars(m) for m in impacted_modules],
            "impacted_apis": impacted_apis,
            "regression_areas": sorted(set(regression_areas)),
            "required_test_suites": sorted(required_tests),
            "consumer_apps": sorted(consumer_apps),
            "direct_impact_count": len(direct),
            "transitive_impact_count": len(transitive),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _normalize(self, path: str) -> str:
        p = Path(path)
        try:
            return str(p.relative_to(self.repo_path)).replace("\\", "/")
        except ValueError:
            return str(p).replace("\\", "/")

    def _classify(self, path: str, proximity: str) -> ImpactedModule:
        module_type = self._detect_type(path)
        owners = self.ownership.get_owners(path)
        risk_factors = self._detect_risk_factors(path, module_type)
        return ImpactedModule(path, module_type, proximity, owners, risk_factors)

    def _detect_type(self, path: str) -> str:
        if any(p.search(path) for p in _TEST_PATH_PATTERNS):
            return "test"
        if any(p.search(path) for p in _DB_PATH_PATTERNS):
            return "database"
        if any(p.search(path) for p in _CONFIG_PATH_PATTERNS):
            return "config"
        if any(p.search(path) for p in _UI_PATH_PATTERNS):
            return "ui_component"

        full_path = self.repo_path / path
        if full_path.exists():
            try:
                content = full_path.read_text(encoding="utf-8", errors="ignore")
                if any(p.search(content) for p in _API_CONTENT_PATTERNS):
                    return "api_endpoint"
            except OSError:
                pass

        lower = path.lower()
        if any(x in lower for x in ("controller", "handler", "endpoint", "route", "resource")):
            return "api_endpoint"
        if any(x in lower for x in ("service", "usecase", "interactor", "business")):
            return "service"
        if any(x in lower for x in ("util", "helper", "common", "shared", "lib", "core")):
            return "library"
        return "module"

    def _detect_risk_factors(self, path: str, module_type: str) -> List[str]:
        factors: List[str] = []
        lower = path.lower()

        if module_type == "api_endpoint":
            factors.append("public_api_surface")
        if module_type == "database":
            factors.append("data_schema_change")
        if module_type == "config":
            factors.append("configuration_change")
        if module_type == "library":
            factors.append("shared_dependency")
        if any(x in lower for x in ("auth", "security", "jwt", "oauth", "permission", "role")):
            factors.append("security_sensitive")
        if any(x in lower for x in ("payment", "billing", "invoice", "transaction", "stripe", "paypal")):
            factors.append("financial_critical")
        if any(x in lower for x in ("notification", "email", "sms", "webhook")):
            factors.append("external_integration")

        return factors

    def _collect_outputs(
        self,
        module: ImpactedModule,
        apis: List[Dict],
        regressions: List[str],
        tests: Set[str],
        consumers: Set[str],
    ) -> None:
        if module.module_type == "api_endpoint":
            apis.append({"path": module.path, "owners": module.owners, "proximity": module.change_proximity})

        if module.module_type in ("api_endpoint", "service", "database", "library"):
            regressions.append(f"[{module.module_type}] {module.path}")

        # Map each affected module to a recommended test suite.
        # Skip test files themselves — they are the tests, not the subject of tests.
        dir_part = "/".join(module.path.split("/")[:-1]) or "."
        if module.module_type == "test":
            pass  # test files run as-is; no additional suite recommendation needed
        elif module.module_type == "api_endpoint":
            tests.add(f"integration/{dir_part}")
        elif module.module_type == "database":
            tests.add("integration/database")
        elif module.module_type == "ui_component":
            tests.add(f"e2e/{dir_part}")
        else:
            tests.add(f"unit/{dir_part}")

        # Derive consumer app name from top-level directory
        parts = module.path.split("/")
        if len(parts) > 1 and parts[0] not in ("src", "lib", "common", "shared", "packages"):
            consumers.add(parts[0])
