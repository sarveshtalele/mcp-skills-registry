"""
Dependency Graph Builder
Parses source files across multiple languages and builds a directed
dependency graph (adjacency list). The reverse graph enables O(V+E)
transitive-impact traversal for any set of changed files.
"""
import ast
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class DependencyGraph:
    nodes: Set[str] = field(default_factory=set)
    edges: Dict[str, Set[str]] = field(default_factory=dict)          # src -> deps
    reverse_edges: Dict[str, Set[str]] = field(default_factory=dict)  # dep -> dependents
    language_map: Dict[str, str] = field(default_factory=dict)        # path -> language

    def add_edge(self, source: str, dep: str) -> None:
        self.nodes.add(source)
        self.nodes.add(dep)
        self.edges.setdefault(source, set()).add(dep)
        self.reverse_edges.setdefault(dep, set()).add(source)

    def get_reverse_deps(self, node: str, transitive: bool = True) -> Set[str]:
        """Return every file that will be affected if `node` changes."""
        if not transitive:
            return set(self.reverse_edges.get(node, set()))

        visited: Set[str] = set()
        queue = list(self.reverse_edges.get(node, set()))
        while queue:
            current = queue.pop()
            if current not in visited:
                visited.add(current)
                queue.extend(self.reverse_edges.get(current, set()))
        return visited


class DependencyGraphBuilder:
    LANGUAGE_MAP = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        ".java": "java",
        ".cs": "csharp",
        ".go": "go",
    }

    IGNORE_DIRS = {
        "node_modules", ".git", "__pycache__", ".venv", "venv",
        "dist", "build", "bin", "obj", ".tox", "coverage",
        ".pytest_cache", ".mypy_cache", "migrations", ".cache",
        "vendor", "target", "out",
    }

    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path
        self.graph = DependencyGraph()

    def build(self) -> DependencyGraph:
        for file_path in self._walk():
            self._process_file(file_path)
        return self.graph

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _walk(self) -> List[Path]:
        result = []
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS and not d.startswith(".")]
            for name in files:
                p = Path(root) / name
                if p.suffix in self.LANGUAGE_MAP:
                    result.append(p)
        return result

    def _rel(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.repo_path)).replace("\\", "/")
        except ValueError:
            return str(path).replace("\\", "/")

    def _process_file(self, file_path: Path) -> None:
        lang = self.LANGUAGE_MAP[file_path.suffix]
        rel = self._rel(file_path)
        self.graph.nodes.add(rel)
        self.graph.language_map[rel] = lang

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return

        extractors = {
            "python": self._py_imports,
            "javascript": self._js_imports,
            "typescript": self._js_imports,
            "java": self._java_imports,
            "csharp": self._cs_imports,
            "go": self._go_imports,
        }
        deps = extractors[lang](content, file_path)
        for dep in deps:
            if dep:
                self.graph.add_edge(rel, dep)

    # ------------------------------------------------------------------
    # Language-specific import extractors
    # ------------------------------------------------------------------

    def _py_imports(self, content: str, file_path: Path) -> List[str]:
        imports: List[str] = []
        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Regex fallback for syntax errors / unsupported syntax versions
            for m in re.finditer(r"^(?:from\s+([\w.]+)|import\s+([\w.]+))", content, re.MULTILINE):
                mod = m.group(1) or m.group(2)
                resolved = self._resolve_py(mod, file_path)
                if resolved:
                    imports.append(resolved)
            return imports

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    r = self._resolve_py(alias.name, file_path)
                    if r:
                        imports.append(r)
            elif isinstance(node, ast.ImportFrom) and node.module:
                r = self._resolve_py(node.module, file_path, node.level or 0)
                if r:
                    imports.append(r)
        return imports

    def _resolve_py(self, module: str, from_file: Path, level: int = 0) -> Optional[str]:
        parts = module.split(".")
        if level > 0:
            # Explicit relative import: level=1 means same package, level=2 means parent
            base = from_file.parent
            for _ in range(level - 1):
                base = base.parent
            candidates = [base.joinpath(*parts)]
        else:
            # Absolute import: try repo root first, then walk up from the file's
            # directory (covers projects that add a sub-directory to sys.path,
            # e.g. `from engine.foo import X` when cwd is `scripts/`).
            candidates = [self.repo_path.joinpath(*parts)]
            ancestor = from_file.parent
            while ancestor != self.repo_path and ancestor != ancestor.parent:
                candidates.append(ancestor.joinpath(*parts))
                ancestor = ancestor.parent

        for candidate in candidates:
            if Path(str(candidate) + ".py").exists():
                return self._rel(Path(str(candidate) + ".py"))
            if (candidate / "__init__.py").exists():
                return self._rel(candidate / "__init__.py")
        return None

    def _js_imports(self, content: str, file_path: Path) -> List[str]:
        imports: List[str] = []
        patterns = [
            r"""(?:import\s+(?:.*?from\s+)?|require\s*\(\s*)['"](\.\.?/[^'"]+)['"]""",
        ]
        for pattern in patterns:
            for m in re.finditer(pattern, content):
                resolved = self._resolve_js(m.group(1), file_path)
                if resolved:
                    imports.append(resolved)
        return imports

    def _resolve_js(self, rel_path_str: str, from_file: Path) -> Optional[str]:
        base = from_file.parent / rel_path_str
        for suffix in ("", ".js", ".ts", ".jsx", ".tsx", "/index.js", "/index.ts"):
            candidate = Path(str(base) + suffix)
            if candidate.exists():
                return self._rel(candidate)
        return None

    def _java_imports(self, content: str, _file: Path) -> List[str]:
        imports: List[str] = []
        for m in re.finditer(r"^import\s+([\w.]+);", content, re.MULTILINE):
            pkg = m.group(1)
            parts = pkg.split(".")
            candidate = self.repo_path.joinpath(*parts[:-1], parts[-1] + ".java")
            if candidate.exists():
                imports.append(self._rel(candidate))
        return imports

    def _cs_imports(self, content: str, _file: Path) -> List[str]:
        imports: List[str] = []
        for m in re.finditer(r"^using\s+([\w.]+);", content, re.MULTILINE):
            ns = m.group(1)
            parts = ns.split(".")

            # Candidate folder/file strategies (in priority order):
            #   1. Folder named exactly as the full namespace  → ProductLaunch.Entities/
            #   2. Folder named as namespace parts[1:] joined  → Entities/
            #   3. Single .cs file by last namespace part       → Entities.cs
            candidate_dirs = [
                self.repo_path / ".".join(parts),            # ProductLaunch.Entities/
                self.repo_path.joinpath(*parts[1:]),          # Entities/
                self.repo_path / ".".join(parts[:-1]),        # ProductLaunch/
            ]

            resolved = False
            for folder in candidate_dirs:
                if folder.is_dir():
                    # Add edges to all meaningful .cs files in the folder
                    for cs_file in sorted(folder.glob("*.cs")):
                        name = cs_file.name.lower()
                        if not any(skip in name for skip in ("designer", "assemblyinfo", "generated")):
                            imports.append(self._rel(cs_file))
                    resolved = True
                    break

            if not resolved:
                # Fall back to a single-file match
                for suffix in (".cs", "Controller.cs", "Service.cs", "Repository.cs", "Handler.cs"):
                    for folder in candidate_dirs:
                        full = Path(str(folder) + suffix)
                        if full.exists():
                            imports.append(self._rel(full))
                            resolved = True
                            break
                    if resolved:
                        break

        return imports

    def _go_imports(self, content: str, _file: Path) -> List[str]:
        imports: List[str] = []
        # Match relative-style Go imports that live inside the repo
        for m in re.finditer(r'"([^"]+)"', content):
            pkg = m.group(1)
            if "/" in pkg:
                parts = pkg.lstrip("/").split("/")
                candidate = self.repo_path.joinpath(*parts)
                go_file = candidate / (parts[-1] + ".go")
                if go_file.exists():
                    imports.append(self._rel(go_file))
        return imports
