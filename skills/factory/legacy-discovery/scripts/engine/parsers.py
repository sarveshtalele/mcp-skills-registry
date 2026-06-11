"""
Language Parsers
================
Provides regex-based static analysis for Python, Java, .NET (C#/VB), and
JavaScript/TypeScript source files.

Each ``parse_X`` function accepts a file path and its raw source text and
returns a normalised dictionary describing the structural elements found in
that file.  The top-level dispatcher :func:`parse_file` routes a
``{"path": ..., "content": ...}`` record returned by
:mod:`engine.loaders` to the correct language-specific parser.

The parsers intentionally favour recall over precision: they are designed
to surface as many meaningful structures as possible from production
codebases, at the cost of occasionally picking up false positives (e.g.
string literals that look like class names).  Results are always validated
and deduplicated before being returned.
"""

import re
from pathlib import Path


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

def detect_language(file_name):
    """Map a filename to a canonical language identifier.

    Args:
        file_name (str): Filename or path whose extension determines the
            language (e.g. ``"OrderController.cs"``).

    Returns:
        str | None: One of ``"python"``, ``"java"``, ``"dotnet"``,
        ``"typescript"``, ``"javascript"``, ``"vbnet"``, ``"go"``,
        ``"ruby"``, ``"php"``, ``"swift"``, ``"kotlin"``, ``"cpp"``,
        or ``None`` when the extension is unrecognised.
    """
    ext_map = {
        ".py":  "python",
        ".java": "java",
        ".cs":  "dotnet",
        ".ts":  "typescript",
        ".tsx": "typescript",
        ".js":  "javascript",
        ".jsx": "javascript",
        ".vb":  "vbnet",
        ".go":  "go",
        ".rb":  "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt":  "kotlin",
        ".cpp": "cpp",
        ".h":   "cpp",
    }
    for ext, lang in ext_map.items():
        if file_name.endswith(ext):
            return lang
    return None


# ---------------------------------------------------------------------------
# Language-specific parsers
# ---------------------------------------------------------------------------

def parse_python(file_path, code):
    """Parse a Python source file for structural elements and API routes.

    Detects class definitions, top-level functions, instance methods,
    ``import`` / ``from … import`` statements, and route decorators from
    Flask (``@app.route``), FastAPI, and Django REST Framework
    (``@app.get``, ``@router.post``, …).

    Args:
        file_path (str): Absolute path to the source file (used as the
            ``"file"`` key in the returned dict).
        code (str): Raw UTF-8 source text.

    Returns:
        dict: A normalised record with the following keys:

        - ``"file"`` (str): Value of *file_path*.
        - ``"language"`` (str): Always ``"python"``.
        - ``"classes"`` (list[str]): Class names found at module level.
        - ``"methods"`` (list[str]): Instance method names + module-level
          function names combined.
        - ``"imports"`` (list[str]): Deduplicated list of imported module
          names (both ``import X`` and ``from X import …`` forms).
        - ``"dependencies"`` (list[str]): Same as ``"imports"``.
        - ``"routes"`` (list[dict]): Each element has ``"path"``,
          ``"methods"`` (list of HTTP verbs), ``"class"``, and
          ``"method"`` keys.

    Note:
        Route detection covers ``@app.route("…", methods=[…])`` (Flask)
        and ``@app.get / @router.post / …`` (FastAPI / DRF style).
    """
    classes  = re.findall(r'^class\s+(\w+)', code, re.MULTILINE)
    methods  = re.findall(r'^\s+def\s+(\w+)', code, re.MULTILINE)
    funcs    = re.findall(r'^def\s+(\w+)', code, re.MULTILINE)
    imp_s    = re.findall(r'^import\s+([\w\.]+)', code, re.MULTILINE)
    imp_f    = re.findall(r'^from\s+([\w\.]+)\s+import', code, re.MULTILINE)
    all_deps = list(set(imp_s + imp_f))

    routes = []
    # Flask-style: @app.route("/path", methods=["GET","POST"])
    for path, methods_str in re.findall(
        r'@\w+\.route\(["\']([^"\']+)["\'](?:,\s*methods=\[([^\]]*)\])?\)',
        code
    ):
        http_methods = re.findall(r'["\'](\w+)["\']', methods_str) if methods_str else ["GET"]
        routes.append({
            "path": path,
            "methods": http_methods,
            "class": None,
            "method": "view_func",
        })
    # FastAPI / DRF style: @app.get("/path") / @router.post("/path")
    for verb, path in re.findall(
        r'@(?:app|router)\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']',
        code, re.IGNORECASE
    ):
        routes.append({
            "path": path,
            "methods": [verb.upper()],
            "class": None,
            "method": "handler",
        })

    return {
        "file":        file_path,
        "language":    "python",
        "classes":     classes,
        "methods":     methods + funcs,
        "imports":     all_deps,
        "dependencies": all_deps,
        "routes":      routes,
        "db_entities": _extract_db_entities_python(file_path, code, classes),
    }


def parse_java(file_path, code):
    """Parse a Java source file for structural elements and Spring MVC routes.

    Detects class declarations, interface declarations, non-keyword method
    signatures, ``import`` statements, and Spring MVC mapping annotations
    (``@GetMapping``, ``@PostMapping``, ``@PutMapping``, ``@DeleteMapping``,
    ``@PatchMapping``) combined with optional ``@RequestMapping`` class-level
    prefixes.

    Args:
        file_path (str): Absolute path to the source file.
        code (str): Raw UTF-8 source text.

    Returns:
        dict: A normalised record with the following keys:

        - ``"file"`` (str)
        - ``"language"`` (str): Always ``"java"``.
        - ``"classes"`` (list[str]): Class + interface names.
        - ``"methods"`` (list[str]): Method names excluding Java keywords.
        - ``"package"`` (str): Package declaration, or ``""`` if absent.
        - ``"imports"`` (list[str]): Fully-qualified import names.
        - ``"dependencies"`` (list[str]): Deduplicated imports.
        - ``"routes"`` (list[dict]): Spring MVC endpoints.

    Note:
        Route paths are prefixed with the class-level ``@RequestMapping``
        path when present.
    """
    classes  = re.findall(
        r'(?:public|private|protected)?\s*(?:abstract\s+)?class\s+(\w+)', code
    )
    ifaces   = re.findall(r'interface\s+(\w+)', code)
    raw_meth = re.findall(
        r'(?:public|private|protected|static|final|\s)+\s+\w[\w<>\[\]]*\s+(\w+)\s*\(', code
    )
    kw = {
        "if", "for", "while", "switch", "catch", "try", "return",
        "new", "this", "super", "throw", "throws", "else",
    }
    methods  = [m for m in raw_meth if m not in kw]
    imports  = re.findall(r'^import\s+([\w\.]+);', code, re.MULTILINE)
    package  = re.findall(r'^package\s+([\w\.]+);', code, re.MULTILINE)

    routes = []
    base_paths = re.findall(r'@RequestMapping\(["\']([^"\']+)["\']', code)
    base = base_paths[0] if base_paths else ""
    for ann, path in re.findall(
        r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)\(["\']([^"\']+)["\']',
        code
    ):
        verb = ann.replace("Mapping", "").upper()
        routes.append({
            "path": base + path,
            "methods": [verb],
            "class": classes[0] if classes else None,
            "method": "handler",
        })

    return {
        "file":        file_path,
        "language":    "java",
        "classes":     classes + ifaces,
        "methods":     methods,
        "package":     package[0] if package else "",
        "imports":     imports,
        "dependencies": list(set(imports)),
        "routes":      routes,
        "db_entities": _extract_db_entities_java(file_path, code, classes),
    }


def parse_dotnet(file_path, code):
    """Parse a C# source file for structural elements and ASP.NET Core routes.

    Detects class declarations, interface declarations, method signatures,
    ``using`` directives, ``namespace`` declarations, and ASP.NET Core HTTP
    verb attributes (``[HttpGet]``, ``[HttpPost]``, ``[HttpPut]``,
    ``[HttpDelete]``, ``[HttpPatch]``, ``[Route]``) combined with a
    class-level ``[Route]`` prefix when present.

    The route extractor performs a two-pass scan: first collecting all HTTP
    attribute positions, then searching a 600-character lookahead window for
    the next method signature to associate each attribute with a handler name.

    Args:
        file_path (str): Absolute path to the source file.
        code (str): Raw UTF-8 source text.

    Returns:
        dict: A normalised record with the following keys:

        - ``"file"`` (str)
        - ``"language"`` (str): Always ``"dotnet"``.
        - ``"classes"`` (list[str]): Class + interface names.
        - ``"methods"`` (list[str]): Method names excluding C# keywords.
        - ``"namespace"`` (str): Namespace declaration, or ``""`` if absent.
        - ``"imports"`` (list[str]): Using-directive namespace names.
        - ``"dependencies"`` (list[str]): Deduplicated using-directives.
        - ``"routes"`` (list[dict]): ASP.NET Core action routes with
          ``"class"``, ``"method"``, ``"path"``, and ``"methods"`` keys.

    Note:
        The ``[Route("api/[controller]")]`` convention is preserved verbatim
        in the extracted path; template variables such as ``[controller]``
        are not expanded.
    """
    classes  = re.findall(
        r'(?:public|private|protected|internal|static|\s)+'
        r'\s+(?:(?:abstract|sealed|partial|static)\s+)*class\s+(\w+)',
        code
    )
    ifaces   = re.findall(r'interface\s+(\w+)', code)
    raw_meth = re.findall(
        r'(?:public|private|protected|internal|static|async|virtual|override|\s)+'
        r'\s+[\w<>\[\]\?]+\s+(\w+)\s*\([^)]*\)\s*(?:\{|=>)',
        code
    )
    kw = {
        "if", "for", "while", "foreach", "switch", "using", "lock",
        "catch", "new", "return", "await", "yield", "get", "set",
        "add", "remove",
    }
    methods  = [m for m in raw_meth if m not in kw]
    usings   = re.findall(r'^using\s+([\w\.]+);', code, re.MULTILINE)
    ns       = re.findall(r'^namespace\s+([\w\.]+)', code, re.MULTILINE)

    # Class-level route prefix, e.g. [Route("api/[controller]")]
    ctrl_route_m = re.search(r'\[Route\s*\(\s*["\']([^"\']+)["\']', code)
    ctrl_prefix  = ctrl_route_m.group(1) if ctrl_route_m else ""

    _http_attr_re = re.compile(
        r'\[(?P<verb>Http(?:Get|Post|Put|Delete|Patch)|Route)\s*'
        r'(?:\(\s*["\'](?P<path>[^"\']*)["\'](?:[^)]*))?\]',
        re.IGNORECASE,
    )
    _meth_sig_re = re.compile(
        r'(?:public|protected|internal|private|static|async|virtual|override|\s)+'
        r'[\w<>\[\]\?]+\s+(\w+)\s*\(',
        re.MULTILINE,
    )
    _verb_map = {
        "HttpPost": "POST", "HttpPut": "PUT", "HttpDelete": "DELETE",
        "HttpPatch": "PATCH", "Route": "GET", "HttpGet": "GET",
    }
    _kw = {
        "if", "for", "while", "foreach", "switch", "using", "lock",
        "catch", "new", "return", "await", "yield", "get", "set",
        "add", "remove",
    }

    routes = []
    for m in _http_attr_re.finditer(code):
        verb = _verb_map.get(m.group("verb"), "GET")
        path = m.group("path") or ""
        # Scan up to 600 chars ahead for the method name.
        window = code[m.end(): m.end() + 600]
        sm = _meth_sig_re.search(window)
        if sm and sm.group(1) not in _kw:
            rel = ("/" + path) if path and not path.startswith("/") else (path or "")
            full_path = (
                ("/" + ctrl_prefix.rstrip("/") + rel)
                if ctrl_prefix
                else (rel or "/api")
            )
            routes.append({
                "class":   classes[0] if classes else None,
                "method":  sm.group(1),
                "path":    full_path,
                "methods": [verb],
            })

    return {
        "file":        file_path,
        "language":    "dotnet",
        "classes":     classes + ifaces,
        "methods":     methods,
        "namespace":   ns[0] if ns else "",
        "imports":     usings,
        "dependencies": list(set(usings)),
        "routes":      routes,
        "db_entities": _extract_db_entities_dotnet(file_path, code, classes + ifaces),
    }


def parse_js_ts(file_path, code):
    """Parse a JavaScript or TypeScript source file for structural elements.

    Detects ES6 class declarations, TypeScript interface declarations,
    function declarations (named functions, arrow functions assigned to
    ``const`` / ``let`` / ``var``), ES module ``import … from`` statements,
    CommonJS ``require()`` calls, and Express-style route registrations
    (``app.get``, ``router.post``, …).

    Args:
        file_path (str): Absolute path to the source file.  The extension
            (``.ts`` / ``.tsx``) is used to distinguish TypeScript from
            JavaScript.
        code (str): Raw UTF-8 source text.

    Returns:
        dict: A normalised record with the following keys:

        - ``"file"`` (str)
        - ``"language"`` (str): ``"typescript"`` or ``"javascript"``.
        - ``"classes"`` (list[str]): ES6 class + TypeScript interface names.
        - ``"methods"`` (list[str]): Deduplicated function/arrow-function
          names.
        - ``"imports"`` (list[str]): Deduplicated module specifiers from
          ``import … from`` and ``require()`` calls.
        - ``"dependencies"`` (list[str]): Same as ``"imports"``.
        - ``"routes"`` (list[dict]): Express route registrations.

    Note:
        TypeScript interface names are only extracted when the detected
        language is ``"typescript"``; they are omitted for plain JavaScript
        to avoid false positives.
    """
    lang    = "typescript" if file_path.endswith((".ts", ".tsx")) else "javascript"
    classes = re.findall(r'class\s+(\w+)', code)
    ifaces  = re.findall(r'interface\s+(\w+)', code) if lang == "typescript" else []
    raw     = re.findall(
        r'(?:function\s+(\w+)|'
        r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\(|(?:\w+\s*=>)))',
        code,
    )
    funcs   = list({f[0] or f[1] for f in raw if f[0] or f[1]})
    imports = re.findall(r'from\s+["\']([^"\']+)["\']', code)
    imports += re.findall(r'require\(["\']([^"\']+)["\']\)', code)

    routes = []
    for verb, path in re.findall(
        r'(?:app|router)\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']',
        code, re.I
    ):
        routes.append({"path": path, "methods": [verb.upper()], "class": None, "method": "handler"})

    return {
        "file": file_path,
        "language": lang,
        "classes": classes + ifaces,
        "methods": funcs,
        "imports": list(set(imports)),
        "dependencies": list(set(imports)),
        "routes": routes,
    }


# ---------------------------------------------------------------------------
# Database entity extraction helpers
# ---------------------------------------------------------------------------

def _extract_db_entities_dotnet(file_path, code, classes):
    """Heuristically extract EF Core database entity definitions from C# code.

    Detects two patterns:

    1. **DbContext subclasses** — collects ``DbSet<X>`` table registrations.
    2. **Domain/model classes** — identifies entities by navigation properties
       or EF attribute presence and extracts scalar fields and relationships.

    Args:
        file_path (str): Absolute path to the source file.
        code (str): Raw source text.
        classes (list[str]): Class names already extracted by
            :func:`parse_dotnet`.

    Returns:
        list[dict]: Each dict has ``"name"``, ``"table"``, ``"fields"``,
        ``"relationships"``, and ``"file"`` keys.
    """
    entities = []

    # Pattern 1: DbContext subclass → DbSet<X> registrations
    if re.search(r'class\s+\w+\s*[:(][^{]*DbContext', code):
        for entity_name in re.findall(r'\bDbSet<(\w+)>', code):
            entities.append({
                "name":          entity_name,
                "table":         entity_name,
                "fields":        [],
                "relationships": [],
                "file":          file_path,
                "is_dbcontext":  True,
            })
        return entities

    # Pattern 2: entity/domain model classes
    # Qualifying signals — at least one must be present
    # Note: nopCommerce uses file-scoped namespaces like "namespace Nop.Core.Domain.Customers;"
    is_entity_file = bool(
        re.search(r'namespace\s+[\w.]*Domain[\w.]*', code, re.IGNORECASE) or
        re.search(r'public\s+virtual\s+(?:ICollection|IList|IEnumerable|HashSet)<', code) or
        re.search(r'\[(?:Key|Table|Column|ForeignKey|Required)\]', code) or
        re.search(r':\s*BaseEntity\b', code)
    )
    if not is_entity_file:
        return entities

    _scalar = (
        r'(?:string|int|long|decimal|bool|DateTime|DateTimeOffset'
        r'|Guid|double|float|byte|short|char|uint|ulong|ushort)'
    )
    for cls in classes:
        fields = []
        rels   = []

        # Scalar properties (potential DB columns)
        for prop in re.findall(
            rf'public\s+{_scalar}\??\s+(\w+)\s*\{{\s*get\s*;', code
        ):
            fields.append(prop)

        # One-to-many navigation properties
        for nav_type, nav_prop in re.findall(
            r'public\s+virtual\s+(?:ICollection|IList|IEnumerable|HashSet)'
            r'<(\w+)>\s+(\w+)\s*\{',
            code,
        ):
            if nav_type != cls:
                rels.append({
                    "type":     "one-to-many",
                    "target":   nav_type,
                    "property": nav_prop,
                })

        # Many-to-one navigation properties
        for nav_type, nav_prop in re.findall(
            r'public\s+virtual\s+(\w+)\s+(\w+)\s*\{\s*get\s*;', code
        ):
            nav_low = nav_type.lower()
            if nav_low not in {
                'string', 'int', 'long', 'bool', 'datetime', 'datetimeoffset',
                'guid', 'decimal', 'double', 'float', 'byte', 'short',
            } and nav_type != cls:
                rels.append({
                    "type":     "many-to-one",
                    "target":   nav_type,
                    "property": nav_prop,
                })

        if fields or rels:
            entities.append({
                "name":          cls,
                "table":         cls,
                "fields":        list(dict.fromkeys(fields)),
                "relationships": rels,
                "file":          file_path,
            })

    return entities


def _extract_db_entities_java(file_path, code, classes):
    """Heuristically extract JPA/Hibernate entity definitions from Java code.

    Args:
        file_path (str): Absolute path to the source file.
        code (str): Raw source text.
        classes (list[str]): Class names already extracted by
            :func:`parse_java`.

    Returns:
        list[dict]: Each dict has ``"name"``, ``"table"``, ``"fields"``,
        ``"relationships"``, and ``"file"`` keys.
    """
    entities = []
    if not re.search(r'@Entity\b', code):
        return entities

    for cls in classes:
        # @Entity annotation must precede the class declaration
        if not re.search(
            rf'@Entity[^@]*?(?:@Table[^)]*\))?\s*(?:public\s+)?class\s+{re.escape(cls)}\b',
            code,
            re.DOTALL,
        ):
            continue

        table_m = re.search(r'@Table\s*\([^)]*name\s*=\s*["\'](\w+)', code)
        table   = table_m.group(1) if table_m else cls.lower() + 's'

        fields = re.findall(
            r'private\s+(?:static\s+|final\s+)?[\w<>]+\s+(\w+)\s*;', code
        )[:15]

        rels = []
        for ann, target, prop in re.findall(
            r'@(ManyToOne|OneToMany|ManyToMany|OneToOne)[^@]*?'
            r'(?:List|Set|Collection|Optional)?<(\w+)>\s+(\w+)',
            code,
            re.DOTALL,
        ):
            rels.append({
                "type":     ann.lower().replace("to", "-to-"),
                "target":   target,
                "property": prop,
            })

        entities.append({
            "name":          cls,
            "table":         table,
            "fields":        list(dict.fromkeys(fields)),
            "relationships": rels,
            "file":          file_path,
        })

    return entities


def _extract_db_entities_python(file_path, code, classes):
    """Heuristically extract SQLAlchemy and Django ORM entity definitions.

    Args:
        file_path (str): Absolute path to the source file.
        code (str): Raw source text.
        classes (list[str]): Class names already extracted by
            :func:`parse_python`.

    Returns:
        list[dict]: Each dict has ``"name"``, ``"table"``, ``"fields"``,
        ``"relationships"``, and ``"file"`` keys.
    """
    entities  = []
    is_alchemy = bool(re.search(r'Column\s*\(|declarative_base\(\)|from\s+sqlalchemy', code))
    is_django  = bool(re.search(r'models\.Model|from\s+django\.db', code))

    if not is_alchemy and not is_django:
        return entities

    for cls in classes:
        if is_django:
            if not re.search(
                rf'class\s+{re.escape(cls)}\s*\([^)]*(?:models\.Model|Model)[^)]*\)', code
            ):
                continue
            fields = re.findall(r'(\w+)\s*=\s*models\.\w+Field\s*\(', code)
            rels   = []
            for prop, target in re.findall(
                r'(\w+)\s*=\s*models\.ForeignKey\s*\(\s*["\']?(\w+)', code
            ):
                rels.append({"type": "many-to-one",  "target": target, "property": prop})
            for prop, target in re.findall(
                r'(\w+)\s*=\s*models\.ManyToManyField\s*\(\s*["\']?(\w+)', code
            ):
                rels.append({"type": "many-to-many", "target": target, "property": prop})
            entities.append({
                "name":          cls,
                "table":         cls.lower() + 's',
                "fields":        list(dict.fromkeys(fields)),
                "relationships": rels,
                "file":          file_path,
            })

        elif is_alchemy:
            if not re.search(rf'class\s+{re.escape(cls)}\s*\([^)]+\)\s*:', code):
                continue
            if not re.search(r'Column\s*\(', code):
                continue
            table_m = re.search(r'__tablename__\s*=\s*["\'](\w+)', code)
            table   = table_m.group(1) if table_m else cls.lower() + 's'
            fields  = re.findall(r'(\w+)\s*=\s*Column\s*\(', code)
            rels    = []
            for prop, target in re.findall(
                r'(\w+)\s*=\s*relationship\s*\(\s*["\'](\w+)', code
            ):
                rels.append({"type": "relationship", "target": target, "property": prop})
            for prop, path in re.findall(
                r'(\w+)\s*=\s*Column\s*\([^)]*ForeignKey\s*\(\s*["\']([^"\']+)', code
            ):
                rels.append({
                    "type":     "foreign-key",
                    "target":   path.split('.')[0],
                    "property": prop,
                })
            entities.append({
                "name":          cls,
                "table":         table,
                "fields":        list(dict.fromkeys(fields)),
                "relationships": rels,
                "file":          file_path,
            })

    return entities


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def parse_file(file_record):
    """Route a file record to the correct language-specific parser.

    Args:
        file_record (dict): A ``{"path": str, "content": str}`` dict as
            returned by :func:`engine.loaders.load_repo`.

    Returns:
        dict | None: The parsed result dict from one of the language-specific
        parsers, or ``None`` if the file extension is not supported by any
        parser.
    """
    path, code = file_record["path"], file_record["content"]
    lang = detect_language(path)
    if lang == "python":
        result = parse_python(path, code)
    elif lang == "java":
        result = parse_java(path, code)
    elif lang == "dotnet":
        result = parse_dotnet(path, code)
    elif lang in ("javascript", "typescript"):
        result = parse_js_ts(path, code)
    else:
        return None
    # Attach raw content so auth-pattern detector and screen detector can scan it
    if result is not None:
        result["content"] = code
    return result
