"""
Analysis Engine
===============
Derives high-level architectural insights from the list of parsed file
records produced by :mod:`engine.parsers`.

Functions in this module operate purely on in-memory data structures — no
filesystem access occurs here (except for ``detect_tech_stack``, which
inspects known config-file locations relative to the repository root).

Typical call order inside the pipeline:

1. :func:`generate_report` — aggregate totals
2. :func:`build_dependency_map` — module-level dependency graph
3. :func:`generate_dep_graph_data` — structured dependency graph (nodes + edges)
4. :func:`extract_api_endpoints` — flat list of routes
5. :func:`generate_openapi_spec` — OpenAPI 3.0 spec dict
6. :func:`detect_dead_code` — unreferenced files and classes
7. :func:`detect_tech_stack` — frameworks and tooling
8. :func:`detect_platform` — runtime platform
9. :func:`detect_architecture_layers` — N-tier layer labels
10. :func:`find_top_modules` — most-connected modules
11. :func:`extract_external_deps` — sorted external dependency list
12. :func:`generate_block_diagram` — structured block diagram (layers + edges)
"""

import re
from pathlib import Path


# ---------------------------------------------------------------------------
# Metrics aggregation
# ---------------------------------------------------------------------------

def generate_report(parsed):
    """Aggregate top-level codebase metrics from all parsed records.

    Args:
        parsed (list[dict]): List of file records as returned by
            :func:`engine.parsers.parse_file`.

    Returns:
        dict: A metrics dict with the following keys:

        - ``"total_files"`` (int): Number of parsed files.
        - ``"languages"`` (dict[str, int]): File count per language.
        - ``"total_classes"`` (int): Sum of classes across all files.
        - ``"total_methods"`` (int): Sum of methods/functions across all
          files.
    """
    report = {
        "total_files": len(parsed),
        "languages": {},
        "total_classes": 0,
        "total_methods": 0,
    }
    for item in parsed:
        lang = item.get("language", "unknown")
        report["languages"][lang] = report["languages"].get(lang, 0) + 1
        report["total_classes"]  += len(item.get("classes", []))
        report["total_methods"]  += len(item.get("methods", []))
    return report


# ---------------------------------------------------------------------------
# Dependency graph
# ---------------------------------------------------------------------------

def build_dependency_map(parsed):
    """Build a module-to-dependencies mapping from parsed records.

    Each module is identified by its filename stem (without extension or
    directory path).  Its value is the set of dependency identifiers
    extracted from ``import`` / ``using`` / ``require`` statements.

    Args:
        parsed (list[dict]): List of file records.

    Returns:
        dict[str, set[str]]: Mapping of ``{module_stem: {dep, …}}``.
    """
    dep_map = {}
    for item in parsed:
        name = Path(item["file"]).stem
        dep_map[name] = set(dep.strip() for dep in item.get("dependencies", []))
    return dep_map


def generate_dep_graph_data(parsed, max_links=80):
    """Build a structured dependency graph from parsed records.

    Returns a JSON-serialisable dict of nodes and directed edges suitable
    for rendering with vis.js (Architecture tab) or any SVG renderer.
    Standard-library / framework root packages are filtered out.

    Args:
        parsed (list[dict]): List of file records.
        max_links (int): Maximum number of edges to emit.  Defaults to 80.

    Returns:
        dict: ``{"nodes": [{"id", "label", "group"}], "edges": [{"from", "to"}]}``
    """
    IGNORE = {
        "java", "javax", "org", "com", "System", "Microsoft", "Newtonsoft",
        "os", "sys", "re", "json", "typing", "collections", "datetime", "math",
        "time", "subprocess", "ast", "pathlib", "abc", "enum", "functools",
        "react", "lodash", "express", "next", "angular", "vue",
    }
    node_ids: dict = {}   # label -> int id
    nodes:    list = []
    edges:    list = []
    seen_edges: set = set()
    nid = 0
    edge_count = 0

    def _get_node(label, group):
        nonlocal nid
        if label not in node_ids:
            node_ids[label] = nid
            nodes.append({"id": nid, "label": label, "group": group})
            nid += 1
        return node_ids[label]

    for item in parsed:
        if edge_count >= max_links:
            break
        src_raw = re.sub(r'[^a-zA-Z0-9_]', '_', Path(item["file"]).stem)
        src_id  = _get_node(src_raw, "module")
        for dep in item.get("dependencies", []):
            root = dep.split(".")[0]
            if root in IGNORE or not root:
                continue
            tgt_raw = re.sub(r'[^a-zA-Z0-9_]', '_', dep.replace(".", "_"))
            if src_raw == tgt_raw or (src_raw, tgt_raw) in seen_edges:
                continue
            seen_edges.add((src_raw, tgt_raw))
            tgt_display = dep.replace("_", ".")
            tgt_id = _get_node(tgt_display, "dependency")
            edges.append({"from": src_id, "to": tgt_id})
            edge_count += 1

    return {"nodes": nodes, "edges": edges}


def generate_graphviz_dot(dep_graph_data):
    """Generate a Graphviz DOT string from dependency graph data dictionary.

    Args:
        dep_graph_data (dict): Dict with "nodes" and "edges" lists.

    Returns:
        str: Valid Graphviz DOT language string.
    """
    dot = [
        "digraph G {",
        "  rankdir=LR;",
        "  splines=true;",
        "  node [shape=box, style=filled, fillcolor=\"#aeaeb2\", color=\"#8e8e93\", fontcolor=\"#1d1d1f\", fontname=\"Helvetica\", fontsize=10];",
        "  edge [color=\"#c7c7cc\", fontname=\"Helvetica\", fontsize=8];"
    ]
    
    nodes = dep_graph_data.get("nodes", [])
    edges = dep_graph_data.get("edges", [])
    
    # Custom node colors by role
    for n in nodes:
        lbl = n.get("label", "")
        nid = n.get("id", "")
        if "controller" in lbl.lower() or "handler" in lbl.lower():
            fill, border, font = "#0071e3", "#005bb5", "#ffffff"
            shape = "box"
        elif "service" in lbl.lower() or "manager" in lbl.lower():
            fill, border, font = "#30d158", "#1a8c3a", "#ffffff"
            shape = "box"
        elif "repository" in lbl.lower() or "repo" in lbl.lower():
            fill, border, font = "#ff9f0a", "#c47900", "#ffffff"
            shape = "box"
        else:
            fill, border, font = "#aeaeb2", "#8e8e93", "#1d1d1f"
            shape = "ellipse"
            
        dot.append(f"  node_{nid} [label=\"{lbl}\", fillcolor=\"{fill}\", color=\"{border}\", fontcolor=\"{font}\", shape=\"{shape}\"];")
        
    for e in edges:
        dot.append(f"  node_{e['from']} -> node_{e['to']};")
        
    dot.append("}")
    return "\n".join(dot)


# Keep the old name as an alias so existing code that may import it still works
def generate_mermaid(parsed, max_links=80):
    """Alias for backward compatibility — returns Graphviz DOT string."""
    return generate_graphviz_dot(generate_dep_graph_data(parsed, max_links))


# ---------------------------------------------------------------------------
# API extraction
# ---------------------------------------------------------------------------

def extract_api_endpoints(parsed):
    """Flatten all route records from parsed files into a single endpoint list.

    Args:
        parsed (list[dict]): List of file records, each potentially
            containing a ``"routes"`` list.

    Returns:
        list[dict]: Each element has the following keys:

        - ``"file"`` (str): Source file path.
        - ``"class"`` (str | None): Containing class name.
        - ``"method"`` (str | None): Handler method name.
        - ``"path"`` (str): HTTP path (e.g. ``"/api/orders/{id}"``).
        - ``"methods"`` (list[str]): HTTP verbs (e.g. ``["GET"]``).
    """
    endpoints = []
    for item in parsed:
        for r in item.get("routes", []):
            endpoints.append({
                "file":    item["file"],
                "class":   r.get("class"),
                "method":  r.get("method"),
                "path":    r.get("path", "/"),
                "methods": r.get("methods", ["GET"]),
            })
    return endpoints


def generate_openapi_spec(endpoints, repo_name):
    """Build an OpenAPI 3.0 specification dict from extracted endpoints.

    Path parameters are normalised from ``<name>`` (Python/Flask style) to
    ``{name}`` (OpenAPI style).  When no endpoints are found a minimal health
    check path is inserted so the spec remains valid.

    Args:
        endpoints (list[dict]): Endpoint records as returned by
            :func:`extract_api_endpoints`.
        repo_name (str): Repository name used in the spec ``info`` block.

    Returns:
        dict: An OpenAPI 3.0 specification suitable for serialisation to JSON
        or YAML.
    """
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": f"{repo_name} API",
            "version": "1.0.0",
            "description": f"Auto-extracted OpenAPI 3.0 spec from {repo_name}",
        },
        "paths": {},
    }
    for ep in endpoints:
        path = ep["path"]
        if not path.startswith("/"):
            path = "/" + path
        path = path.replace("<", "{").replace(">", "}")
        if path not in spec["paths"]:
            spec["paths"][path] = {}
        for verb in ep["methods"]:
            spec["paths"][path][verb.lower()] = {
                "summary": f"{ep.get('class') or 'global'}.{ep.get('method') or 'handler'}()",
                "description": f"Defined in `{Path(ep['file']).name}`",
                "responses": {"200": {"description": "Success"}},
            }
    if not spec["paths"]:
        spec["paths"]["/health"] = {
            "get": {"summary": "Health check", "responses": {"200": {"description": "OK"}}}
        }
    return spec


# ---------------------------------------------------------------------------
# Dead code detection
# ---------------------------------------------------------------------------

def detect_dead_code(parsed):
    """Heuristically identify unreferenced files and classes.

    A file is considered potentially dead when:
    - Its stem does not appear in any other file's imports/dependencies.
    - None of the classes it defines are referenced by other files.
    - Its name does not contain a well-known entry-point term (``main``,
      ``app``, ``index``, etc.).

    A class is considered potentially dead when its name does not appear in
    any file's import/dependency list and it is not a known entry-point class.

    Args:
        parsed (list[dict]): List of file records.

    Returns:
        dict: A report dict with the following keys:

        - ``"dead_files"`` (list[str]): Absolute paths of potentially
          unreferenced files.
        - ``"dead_classes"`` (list[dict]): Each element has ``"class"`` and
          ``"file"`` keys.

    Note:
        This is a heuristic — dynamic imports, reflection, and unconventional
        naming conventions can produce false positives.  Results should be
        manually reviewed before any code is removed.
    """
    all_refs = set()
    classes_defined = {}
    for item in parsed:
        for dep in item.get("imports", []) + item.get("dependencies", []):
            all_refs.add(dep)
            for part in dep.split("."):
                all_refs.add(part)
        for cls in item.get("classes", []):
            classes_defined[cls] = item["file"]

    entry_terms   = {"main", "setup", "app", "build", "index", "program", "startup", "run", "init"}
    skip_classes  = {"Program", "Startup", "App", "Main", "Application", "Index", "Bootstrap"}

    # For .NET/Java, files are referenced by convention (MVC routing, DI
    # containers, annotation scanning) rather than explicit import statements.
    # Skip well-known architectural-role suffixes to avoid massive false-positive
    # rates — otherwise almost every Controller/Service/Repository gets flagged.
    CONVENTION_SUFFIXES = {
        "controller", "service", "repository", "repo", "model", "viewmodel",
        "factory", "provider", "handler", "extension", "helper", "manager",
        "builder", "configuration", "middleware", "filter", "validator",
        "mapper", "profile", "module", "command", "query", "event",
        "decorator", "interceptor", "adapter", "facade", "gateway",
    }

    dead_files = []
    for item in parsed:
        name      = Path(item["file"]).stem
        name_low  = name.lower()
        if any(t in name_low for t in entry_terms):
            continue
        # Skip files whose names follow a well-known architectural convention
        # in languages where DI/routing resolves references at runtime.
        if item.get("language") in ("dotnet", "java"):
            if any(name_low.endswith(suf) for suf in CONVENTION_SUFFIXES):
                continue
        if name in all_refs:
            continue
        if any(cls in all_refs for cls in item.get("classes", [])):
            continue
        dead_files.append(item["file"])

    dead_classes = []
    for cls, fp in classes_defined.items():
        if cls in skip_classes:
            continue
        if cls not in all_refs:
            dead_classes.append({"class": cls, "file": fp})

    return {"dead_files": dead_files, "dead_classes": dead_classes}


# ---------------------------------------------------------------------------
# Tech stack detection
# ---------------------------------------------------------------------------

def detect_tech_stack(parsed, repo_path):
    """Detect frameworks and tooling from import names and config files.

    Two strategies are combined:

    1. **Import-based**: Checks whether dependency strings (lowercased)
       contain known framework identifiers.
    2. **Config-file-based**: Checks for the presence of well-known config
       files (``package.json``, ``pom.xml``, ``Dockerfile``, etc.) in the
       repository root.

    Args:
        parsed (list[dict]): List of file records.
        repo_path (str): Absolute path to the cloned repository root.

    Returns:
        list[str]: Sorted, deduplicated list of detected technology names
        (e.g. ``["ASP.NET Core", "Docker", "Entity Framework"]``).
    """
    all_deps = set()
    for item in parsed:
        for dep in item.get("dependencies", []):
            all_deps.add(dep.lower())

    techs = []
    checks = [
        ({"microsoft.aspnetcore", "system.web.mvc"},        "ASP.NET Core"),
        ({"system.web"},                                     "ASP.NET Framework (Legacy)"),
        ({"entityframework", "microsoft.entityframeworkcore"}, "Entity Framework"),
        ({"dapper"},                                         "Dapper ORM"),
        ({"nop."},                                           "nopCommerce"),
        ({"org.springframework"},                            "Spring Framework"),
        ({"hibernate"},                                      "Hibernate ORM"),
        ({"django"},                                         "Django"),
        ({"flask"},                                          "Flask"),
        ({"fastapi"},                                        "FastAPI"),
        ({"sqlalchemy"},                                     "SQLAlchemy"),
        ({"react"},                                          "React"),
        ({"angular"},                                        "Angular"),
        ({"express"},                                        "Express.js"),
        ({"nestjs"},                                         "NestJS"),
        ({"next"},                                           "Next.js"),
    ]
    for triggers, label in checks:
        if any(any(t in dep for dep in all_deps) for t in triggers):
            techs.append(label)

    config_checks = [
        ("package.json",       "Node.js"),
        ("pom.xml",            "Apache Maven"),
        ("build.gradle",       "Gradle"),
        ("requirements.txt",   "Python pip"),
        ("Dockerfile",         "Docker"),
        ("docker-compose.yml", "Docker Compose"),
        ("*.csproj",           ".NET Project File"),
        ("*.sln",              ".NET Solution"),
        ("Gemfile",            "Ruby Bundler"),
        ("go.mod",             "Go Modules"),
    ]
    for pattern, label in config_checks:
        if "*" in pattern:
            if list(Path(repo_path).rglob(pattern)):
                techs.append(label)
        elif (Path(repo_path) / pattern).exists():
            techs.append(label)

    return sorted(set(techs))


# ---------------------------------------------------------------------------
# Platform and architecture detection
# ---------------------------------------------------------------------------

def detect_platform(parsed):
    """Infer the primary runtime platform from the dominant language.

    Args:
        parsed (list[dict]): List of file records.

    Returns:
        str: A human-readable platform label such as ``".NET / Windows Server"``
        or ``"Cross-platform"``.
    """
    langs = {r.get("language") for r in parsed}
    if "dotnet"     in langs: return ".NET / Windows Server"
    if "java"       in langs: return "JVM / Linux"
    if "python"     in langs: return "Python / Linux"
    if "typescript" in langs or "javascript" in langs: return "Node.js"
    return "Cross-platform"


def detect_architecture_layers(parsed):
    """Infer N-tier architecture layers from file-path keywords.

    File paths are matched (case-insensitively) against a set of keywords
    associated with each layer.  Any file that matches contributes its layer
    label to the result set.

    Args:
        parsed (list[dict]): List of file records.

    Returns:
        list[str]: Sorted list of detected layer labels, e.g.
        ``["API / Presentation Layer", "Business Logic Layer",
        "Data Access Layer"]``.
    """
    layers = set()
    for item in parsed:
        p = item["file"].lower()
        if any(x in p for x in ["controller", "api", "endpoint", "route", "handler"]):
            layers.add("API / Presentation Layer")
        if any(x in p for x in ["service", "business", "domain", "core", "logic"]):
            layers.add("Business Logic Layer")
        if any(x in p for x in ["repository", "data", "dal", "model", "entity", "db", "database"]):
            layers.add("Data Access Layer")
        if any(x in p for x in ["helper", "util", "common", "shared", "extension"]):
            layers.add("Utility / Shared Layer")
        if any(x in p for x in ["config", "setting", "startup", "program"]):
            layers.add("Configuration / Bootstrap Layer")
        if any(x in p for x in ["view", "template", "razor", "html"]):
            layers.add("View / Template Layer")
    return sorted(layers)


# ---------------------------------------------------------------------------
# Module ranking and dependency extraction
# ---------------------------------------------------------------------------

def find_top_modules(dep_map, n=10):
    """Return the *n* modules with the most outgoing dependency references.

    Args:
        dep_map (dict[str, set[str]]): Dependency map as returned by
            :func:`build_dependency_map`.
        n (int): Number of top modules to return.  Defaults to 10.

    Returns:
        list[tuple[str, int]]: List of ``(module_stem, connection_count)``
        tuples sorted in descending order of connection count.
    """
    counts = {mod: len(deps) for mod, deps in dep_map.items()}
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:n]


def extract_external_deps(parsed):
    """Collect and sort a deduplicated list of all unique dependency identifiers.

    Args:
        parsed (list[dict]): List of file records.

    Returns:
        list[str]: Up to 100 dependency identifiers sorted alphabetically.
    """
    all_deps = set()
    for item in parsed:
        for dep in item.get("dependencies", []):
            all_deps.add(dep)
    return sorted(all_deps)[:100]


# ---------------------------------------------------------------------------
# Database schema and microservice data boundaries
# ---------------------------------------------------------------------------

def detect_database_schema(parsed):
    """Aggregate database entity definitions from all parsed file records.

    Collects ``db_entities`` lists emitted by the language-specific parsers
    and merges duplicate entity names (the same entity class appearing in
    multiple files gets its fields and relationships combined).

    Args:
        parsed (list[dict]): List of file records from
            :func:`engine.parsers.parse_file`.

    Returns:
        dict: A schema summary with the following keys:

        - ``"entities"`` (list[dict]): Merged entity records, each with
          ``"name"``, ``"table"``, ``"fields"``, ``"relationships"``, and
          ``"file"`` keys.
        - ``"entity_count"`` (int): Total unique entities detected.
        - ``"relationship_count"`` (int): Total relationship links found.
        - ``"has_schema"`` (bool): ``True`` when at least one entity was
          detected.
        - ``"context_files"`` (list[str]): Paths of DbContext /
          SessionFactory / declarative-base files.
    """
    seen          = {}
    context_files = []

    for item in parsed:
        for entity in item.get("db_entities", []):
            name = entity.get("name")
            if not name:
                continue
            if entity.get("is_dbcontext"):
                context_files.append(item["file"])
                # Register the entity by name even without full field details yet.
                if name not in seen:
                    seen[name] = {
                        "name":          name,
                        "table":         entity.get("table", name),
                        "fields":        [],
                        "relationships": [],
                        "file":          entity.get("file", item["file"]),
                    }
                continue
            if name not in seen:
                seen[name] = {
                    "name":          name,
                    "table":         entity.get("table", name),
                    "fields":        list(entity.get("fields", [])),
                    "relationships": list(entity.get("relationships", [])),
                    "file":          entity.get("file", item["file"]),
                }
            else:
                existing  = seen[name]
                new_flds  = [f for f in entity.get("fields", [])
                             if f not in existing["fields"]]
                existing["fields"].extend(new_flds)
                existing["relationships"].extend(entity.get("relationships", []))

    entities  = list(seen.values())
    rel_count = sum(len(e["relationships"]) for e in entities)

    return {
        "entities":           entities,
        "entity_count":       len(entities),
        "relationship_count": rel_count,
        "has_schema":         len(entities) > 0,
        "context_files":      list(set(context_files)),
    }


def suggest_microservice_data_boundaries(db_schema, modernization=None):
    """Group entities into bounded contexts for microservice decomposition.

    Uses semantic domain keywords to cluster entity names.  When no entities
    are detected, falls back to the ``microservices_boundaries`` list from the
    AI modernisation roadmap if one is supplied.

    Args:
        db_schema (dict): Schema dict from :func:`detect_database_schema`.
        modernization (dict | None): AI modernisation roadmap dict.  Used as
            a fallback when no entities are detected.

    Returns:
        list[dict]: Each element has the following keys:

        - ``"name"`` (str): Bounded context / proposed microservice name.
        - ``"entities"`` (list[str]): Entity names belonging to this context.
        - ``"color"`` (str): CSS hex colour for visualisation.
        - ``"entity_count"`` (int): Number of entities in this context.
    """
    entities = db_schema.get("entities", [])
    COLORS   = [
        "#0071e3", "#30d158", "#ff9f0a", "#bf5af2",
        "#ff453a", "#5ac8fa", "#ff9500", "#64d2ff",
    ]

    if not entities:
        # Fall back to AI-generated microservice boundaries
        if modernization:
            boundaries = modernization.get("microservices_boundaries", [])
            return [
                {
                    "name":         b,
                    "entities":     [],
                    "color":        COLORS[i % len(COLORS)],
                    "entity_count": 0,
                }
                for i, b in enumerate(boundaries)
            ]
        return []

    # Semantic domain clusters (keywords → bounded context)
    domain_clusters = [
        ("Customer / Identity",  ["customer", "user", "account", "identity", "member",
                                   "profile", "address", "contact", "login", "auth",
                                   "permission", "role", "claim", "token"]),
        ("Product / Catalog",    ["product", "catalog", "category", "item", "sku",
                                   "inventory", "stock", "price", "attribute",
                                   "specification", "brand", "manufacturer", "vendor",
                                   "supplier", "tag", "picture"]),
        ("Order / Commerce",     ["order", "cart", "checkout", "purchase", "payment",
                                   "invoice", "transaction", "shipment", "delivery",
                                   "return", "refund", "discount", "coupon", "gift",
                                   "voucher", "basket"]),
        ("Content / Media",      ["content", "blog", "post", "news", "article", "page",
                                   "topic", "forum", "thread", "message", "comment",
                                   "review", "rating", "media", "file", "image",
                                   "document", "upload", "poll"]),
        ("Notification / Comms", ["notification", "email", "sms", "alert", "campaign",
                                   "newsletter", "subscription", "log", "audit",
                                   "activity", "event"]),
        ("Configuration",        ["setting", "configuration", "config", "locale",
                                   "language", "currency", "tax", "store", "country",
                                   "state", "region", "option", "parameter"]),
        ("Search / Analytics",   ["search", "index", "analytics", "report", "stat",
                                   "metric", "tracking", "session", "visit", "history"]),
    ]

    assigned   = {}
    unassigned = []

    for entity in entities:
        name_low = entity["name"].lower()
        placed   = False
        for domain_name, keywords in domain_clusters:
            if any(kw in name_low for kw in keywords):
                assigned.setdefault(domain_name, []).append(entity["name"])
                placed = True
                break
        if not placed:
            unassigned.append(entity["name"])

    result = []
    for i, (domain_name, entity_names) in enumerate(assigned.items()):
        result.append({
            "name":         domain_name,
            "entities":     entity_names,
            "color":        COLORS[i % len(COLORS)],
            "entity_count": len(entity_names),
        })

    if unassigned:
        result.append({
            "name":         "Core / Infrastructure",
            "entities":     unassigned,
            "color":        COLORS[len(result) % len(COLORS)],
            "entity_count": len(unassigned),
        })

    return result


# ---------------------------------------------------------------------------
# Block diagram generator
# ---------------------------------------------------------------------------

def generate_block_diagram(parsed, endpoints, db_schema, tech_stack):
    """Generate a structured block diagram of the analysed system.

    Returns a JSON-serialisable dict with ``layers`` (list of layer groups,
    each containing named nodes) and ``edges`` (directed connections between
    layers).  The dashboard renders this with a pure-SVG custom renderer —
    no Mermaid.js or external library required.

    Args:
        parsed (list[dict]): File records from :func:`engine.parsers.parse_file`.
        endpoints (list[dict]): API endpoint records.
        db_schema (dict): Schema dict from :func:`detect_database_schema`.
        tech_stack (list[str]): Detected tech stack.

    Returns:
        dict: ``{"layers": [{"id", "label", "color", "nodes": [{"id", "label"}]}],
                "edges": [{"from", "to", "label"}]}``
    """
    import re as _re

    def _safe(name):
        return _re.sub(r'[^A-Za-z0-9]', '_', str(name))

    # Vendor/library stems to skip — these are frontend dependencies, not application classes
    _VENDOR_STEMS = frozenset({
        "bootstrap", "bootstrap_min", "jquery", "jquery_min",
        "modernizr", "modernizr_2_6_2", "respond", "respond_min",
        "moment", "lodash", "angular", "vue", "react",
        "_references", "webforms", "webparts", "detailsview", "gridview",
        "menu", "smartnav", "treeview", "menustandards", "focus",
        "microsoftajax", "microsoftajaxcore", "microsoftajaxcomponentmodel",
        "microsoftajaxapplicationservices", "microsoftajaxwebservices",
        "microsoftajaxglobalization", "microsoftajaxhistory",
        "microsoftajaxnetwork", "microsoftajaxserialization",
        "microsoftajaxtimer", "microsoftajaxwebforms",
    })

    # Classify files and classes into layers using class names and folder heuristics
    controllers, services, repositories = [], [], []
    seen_classes = set()
    seen_components = set()

    for item in parsed[:150]:
        file_path = item.get("file", "")
        file_lower = file_path.lower()

        # Folder-based layer classification (explicit directory keywords only)
        is_presentation = any(k in file_lower for k in (
            "/controllers/", "/api/", "/endpoints/", "/handlers/", "/pages/",
            "\\controllers\\", "\\api\\", "\\endpoints\\", "\\handlers\\", "\\pages\\",
        )) or file_lower.endswith(".aspx") or ".aspx." in file_lower
        # NOTE: .aspx.cs = Web Forms code-behind; .js/.ts/.html are NOT presentation
        # (often vendor scripts or templates, not application controllers).

        is_logic = any(k in file_lower for k in (
            "/services/", "/managers/", "/usecases/", "/business/", "/logic/", "/workflows/",
            "\\services\\", "\\managers\\", "\\usecases\\", "\\business\\", "\\logic\\", "\\workflows\\",
        ))
        is_data = any(k in file_lower for k in (
            "/repositories/", "/repos/", "/dao/", "/dal/", "/store/", "/data/", "/db/",
            "\\repositories\\", "\\repos\\", "\\dao\\", "\\dal\\", "\\store\\", "\\data\\", "\\db\\",
        ))

        # Check classes defined in this file — class names are authoritative
        for cls in item.get("classes", []):
            if cls in seen_classes or not cls:
                continue
            seen_classes.add(cls)
            lower_cls = cls.lower()

            # Presentation: use suffix/prefix checks to avoid false positives
            # (e.g. "page" would match "homepage"; "form" would match "informationforms")
            _is_ctrl_cls = any(lower_cls.endswith(k) or lower_cls.startswith(k) for k in (
                "controller", "handler", "router", "endpoint",
            )) or any(k in lower_cls for k in (
                "controller", "handler", "router",
            ))
            # Web Forms code-behind: class name IS the page name (SignUp, Default, Contact)
            # detected via is_presentation (file path) rather than class name keywords
            _is_svc_cls = any(lower_cls.endswith(k) or k in lower_cls for k in (
                "service", "manager", "usecase", "facade", "workflow", "processor",
            )) or any(lower_cls.endswith(k) for k in ("helper", "validator"))
            _is_data_cls = any(lower_cls.endswith(k) or k in lower_cls for k in (
                "repository", "repo", "dao", "store", "gateway", "adapter",
            )) or lower_cls.endswith("context") or lower_cls.endswith("dbcontext")

            if _is_ctrl_cls or is_presentation:
                if cls not in controllers:
                    controllers.append(cls)
            elif _is_svc_cls or is_logic:
                if cls not in services:
                    services.append(cls)
            elif _is_data_cls or is_data:
                if cls not in repositories:
                    repositories.append(cls)

        # Fallback: file has no classes — use folder + stem signals
        if not item.get("classes"):
            stem = Path(file_path).stem
            # For .aspx.cs files, strip the .aspx suffix from stem (e.g. "SignUp.aspx" → "SignUp")
            if stem.lower().endswith(".aspx"):
                stem = stem[:-5]
            stem_key = _re.sub(r'[^a-z0-9]', '_', stem.lower())
            # Skip vendor/library files entirely
            if stem_key in _VENDOR_STEMS or stem.startswith(("_", ".")):
                continue
            if stem not in seen_components and stem:
                seen_components.add(stem)
                if is_presentation or any(k in file_lower for k in ("controller", "handler", "router", "endpoint")):
                    controllers.append(stem)
                elif is_logic or any(k in file_lower for k in ("service", "manager", "usecase", "facade", "workflow")):
                    services.append(stem)
                elif is_data or any(k in file_lower for k in ("repository", "repo", "dao", "store", "gateway", "adapter", "context")):
                    repositories.append(stem)

    controllers  = controllers[:5]
    services     = services[:5]
    repositories = repositories[:4]
    entities     = [e["name"] for e in (db_schema or {}).get("entities", [])[:5]]

    layers = []
    edges  = []

    # Layer 0: Client — represents external callers (browser, mobile app, API consumer)
    layers.append({
        "id": "client",
        "label": "User / Client",
        "color": "#6e6e73",
        "icon": "user",
        "nodes": [{"id": "client_node", "label": "Web Browser / API Client"}],
    })

    # Layer 1: API / Controllers
    api_nodes = []
    if controllers:
        api_nodes = [{"id": _safe(c), "label": c} for c in controllers]
    elif endpoints:
        ep_groups: dict = {}
        for ep in endpoints[:6]:
            parts = [p for p in ep["path"].split("/")
                     if p and not p.startswith("{") and p.lower() not in ("api", "v1", "v2", "v3")]
            seg = parts[0].title() if parts else "API"
            ep_groups.setdefault(seg, 0)
            ep_groups[seg] += 1
        api_nodes = [{"id": _safe(s) + "_handler", "label": f"{s} ({c} routes)"}
                     for s, c in list(ep_groups.items())[:5]]

    if api_nodes:
        layers.append({
            "id": "api",
            "label": "API / Presentation Layer",
            "color": "#0071e3",
            "icon": "api",
            "nodes": api_nodes,
        })
        for n in api_nodes[:3]:
            edges.append({"from": "client_node", "to": n["id"], "label": "HTTP"})

    # Layer 2: Service / Business Logic
    if services:
        svc_nodes = [{"id": _safe(s), "label": s} for s in services]
        layers.append({
            "id": "service",
            "label": "Business Logic / Service Layer",
            "color": "#30d158",
            "icon": "service",
            "nodes": svc_nodes,
        })
        for i, an in enumerate(api_nodes[:4]):
            sn = svc_nodes[min(i, len(svc_nodes) - 1)]
            edges.append({"from": an["id"], "to": sn["id"], "label": "calls"})

    # Layer 3: Repository / Data Access
    if repositories:
        repo_nodes = [{"id": _safe(r), "label": r} for r in repositories]
        layers.append({
            "id": "repo",
            "label": "Data Access / Repository Layer",
            "color": "#ff9f0a",
            "icon": "repo",
            "nodes": repo_nodes,
        })
        src_layer = services if services else (controllers if controllers else [])
        for i, s in enumerate(src_layer[:4]):
            rn = repo_nodes[min(i, len(repo_nodes) - 1)]
            edges.append({"from": _safe(s), "to": rn["id"], "label": "data ops"})
    elif entities:
        orm_nodes = [{"id": "orm_node", "label": "ORM / Data Mapper"}]
        layers.append({
            "id": "repo",
            "label": "Data Access Layer",
            "color": "#ff9f0a",
            "icon": "repo",
            "nodes": orm_nodes,
        })

    # Layer 4: Database entities
    if entities:
        db_nodes = [{"id": "db_" + _safe(e), "label": e} for e in entities]
        layers.append({
            "id": "database",
            "label": "Database",
            "color": "#bf5af2",
            "icon": "db",
            "nodes": db_nodes,
        })
        repo_layer = next((l for l in layers if l["id"] == "repo"), None)
        if repo_layer:
            for i, rn in enumerate(repo_layer["nodes"][:3]):
                dn = db_nodes[min(i, len(db_nodes) - 1)]
                edges.append({"from": rn["id"], "to": dn["id"], "label": "SQL/ORM"})

    # Layer 5: External Services (from tech stack)
    ext_map = {
        "redis":    ("cache",   "Redis Cache"),
        "kafka":    ("queue",   "Kafka / MQ"),
        "rabbitmq": ("queue",   "RabbitMQ"),
        "email":    ("email",   "Email / SMTP"),
        "smtp":     ("email",   "Email / SMTP"),
        "s3":       ("storage", "Cloud Storage"),
        "azure":    ("cloud",   "Azure"),
        "aws":      ("cloud",   "AWS"),
        "stripe":   ("payment", "Payment Gateway"),
        "paypal":   ("payment", "Payment Gateway"),
        "oauth":    ("auth",    "Auth / OAuth"),
        "jwt":      ("auth",    "Auth / JWT"),
    }
    shown_ext: set = set()
    ext_nodes = []
    stack_lower = " ".join(tech_stack).lower()
    for kw, (group, label) in ext_map.items():
        if kw in stack_lower and group not in shown_ext:
            shown_ext.add(group)
            ext_nodes.append({"id": "ext_" + group, "label": label})

    if ext_nodes[:4]:
        layers.append({
            "id": "external",
            "label": "External Services",
            "color": "#ff453a",
            "icon": "ext",
            "nodes": ext_nodes[:4],
        })
        # Connect service layer (or API layer) to external services
        src_ids = ([_safe(s) for s in services[:2]] or
                   [n["id"] for n in api_nodes[:2]])
        for sid in src_ids:
            for en in ext_nodes[:2]:
                edges.append({"from": sid, "to": en["id"], "label": "integrates"})

    return {"layers": layers, "edges": edges}


def generate_block_diagram_dot(block_diagram_data):
    """Generate a Graphviz DOT string for the block diagram layers.

    Args:
        block_diagram_data (dict): Dict with "layers" and "edges" lists.

    Returns:
        str: Graphviz DOT representation of block diagram.
    """
    if not block_diagram_data or "layers" not in block_diagram_data:
        return "digraph G { A [label=\"No diagram generated\"]; }"
        
    dot = [
        "digraph G {",
        "  rankdir=TB;",
        "  splines=ortho;",
        "  nodesep=0.4;",
        "  ranksep=0.5;",
        "  bgcolor=\"transparent\";",
        "  node [shape=box, style=\"filled,rounded\", fontname=\"Helvetica\", fontsize=11, fillcolor=\"#f5f5f7\", fontcolor=\"#1d1d1f\", penwidth=1.5];",
        "  edge [color=\"#8e8e93\", fontname=\"Helvetica\", fontsize=9, fontcolor=\"#8e8e93\", arrowhead=vee, arrowsize=0.7];"
    ]
    
    layers = block_diagram_data.get("layers", [])
    edges = block_diagram_data.get("edges", [])
    
    for i, layer in enumerate(layers):
        dot.append(f"  subgraph cluster_{i} {{")
        dot.append(f"    label = \"{layer.get('label', '')}\";")
        dot.append(f"    color = \"{layer.get('color', '#aeaeb2')}\";")
        dot.append(f"    style = \"dashed,rounded\";")
        dot.append(f"    fontname = \"Helvetica\";")
        dot.append(f"    fontsize = 12;")
        dot.append(f"    fontcolor = \"{layer.get('color', '#1d1d1f')}\";")
        dot.append(f"    penwidth = 2.0;")
        
        for node in layer.get("nodes", []):
            dot.append(f"    \"{node['id']}\" [label=\"{node.get('label', '')}\", fillcolor=\"{layer.get('color', '#f5f5f7')}\", fontcolor=\"#ffffff\", style=\"filled,rounded\", penwidth=0];")
        dot.append("  }")
        
    for edge in (edges or []):
        dot.append(f"  \"{edge['from']}\" -> \"{edge['to']}\" [label=\"{edge.get('label', '')}\"];")

    dot.append("}")
    return "\n".join(dot)


def generate_block_diagram_svg(block_diagram_data):
    """Generate a premium, responsive SVG image for the layered block diagram.

    Args:
        block_diagram_data (dict): Layer and edge data structures.

    Returns:
        str: Self-contained XML SVG content.
    """
    if not block_diagram_data or "layers" not in block_diagram_data:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="50"><text x="10" y="30">No diagram generated</text></svg>'

    layers = block_diagram_data.get("layers", [])
    edges = block_diagram_data.get("edges", [])

    layer_height = 100
    layer_gap = 40
    total_layers = len(layers)
    total_height = 20 + total_layers * (layer_height + layer_gap) - layer_gap + 20

    # Helper: truncate long labels to prevent pill overflow
    def _trunc(lbl, max_chars=18):
        return lbl if len(lbl) <= max_chars else lbl[:max_chars - 1] + "…"

    # Helper: hex color to semi-transparent CSS rgba (20% opacity fill)
    def _tint(hex_color):
        h = hex_color.lstrip("#")
        if len(h) == 6:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return f"rgba({r},{g},{b},0.15)"
        return "rgba(174,174,178,0.15)"

    svg_parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="700" height="{total_height}" viewBox="0 0 700 {total_height}">',
        '  <style>',
        '    .layer-bg { fill: #f9f9fb; stroke: #e5e5ea; stroke-width: 1.5; }',
        '    .layer-title { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.6px; }',
        '    .node-text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; font-size: 11px; font-weight: 600; text-anchor: middle; dominant-baseline: middle; }',
        '    .connector-line { stroke: #aeaeb2; stroke-width: 2; stroke-dasharray: 4 3; }',
        '    .connector-arrow { fill: #aeaeb2; }',
        '    .connector-text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; font-size: 9px; fill: #6e6e73; font-weight: 600; text-anchor: middle; }',
        '  </style>',
    ]

    for idx, layer in enumerate(layers):
        y = 20 + idx * (layer_height + layer_gap)
        color = layer.get("color", "#8e8e93")
        label = layer.get("label", "Layer").upper()
        nodes = layer.get("nodes", [])
        tint = _tint(color)

        # Background card with subtle left border via thick path
        svg_parts.append(f'  <!-- Layer {idx}: {label} -->')
        svg_parts.append(f'  <rect x="25" y="{y}" width="650" height="{layer_height}" rx="12" class="layer-bg" stroke="{color}" stroke-opacity="0.25" />')
        svg_parts.append(f'  <rect x="25" y="{y}" width="6" height="{layer_height}" rx="3" fill="{color}" />')

        # Layer title
        svg_parts.append(f'  <text x="44" y="{y + 22}" fill="{color}" class="layer-title">{label}</text>')

        # Node pills
        if nodes:
            num_nodes = len(nodes)
            max_pill_w = 120
            min_pill_w = 80
            pill_h = 30
            usable_w = 580  # inside the card (44..674)
            spacing = min(max_pill_w + 14, (usable_w - min_pill_w) // max(1, num_nodes - 1)) if num_nodes > 1 else 0
            total_pills_w = (num_nodes - 1) * spacing + max_pill_w
            start_x = 44 + (usable_w - total_pills_w) // 2  # center horizontally
            y_center = y + 60

            for j, node in enumerate(nodes):
                node_lbl = _trunc(node.get("label", ""))
                pill_w = max(min_pill_w, min(max_pill_w, len(node_lbl) * 7 + 24))
                cx = start_x + j * spacing + pill_w // 2  # pill center x

                pill_x = cx - pill_w // 2
                pill_y = y_center - pill_h // 2

                # Pill: tinted layer color background + colored border
                svg_parts.append(f'  <rect x="{pill_x}" y="{pill_y}" width="{pill_w}" height="{pill_h}" rx="7" fill="{tint}" stroke="{color}" stroke-width="1.5" />')
                # Colored dot
                svg_parts.append(f'  <circle cx="{pill_x + 11}" cy="{y_center}" r="3" fill="{color}" />')
                # Node label (colored text)
                svg_parts.append(f'  <text x="{pill_x + 11 + 6 + (pill_w - 11 - 6) // 2}" y="{y_center + 1}" fill="{color}" class="node-text">{node_lbl}</text>')

        # Connector between this layer and the next
        if idx < total_layers - 1:
            current_node_ids = {n["id"] for n in nodes}
            next_nodes = layers[idx + 1].get("nodes", [])
            next_node_ids = {n["id"] for n in next_nodes}

            edge_labels = []
            for edge in edges:
                if edge.get("from") in current_node_ids and edge.get("to") in next_node_ids:
                    lbl = edge.get("label", "")
                    if lbl and lbl not in edge_labels:
                        edge_labels.append(lbl)

            connector_label = edge_labels[0] if edge_labels else ""
            y_start = y + layer_height
            y_end = y_start + layer_gap
            y_mid = (y_start + y_end) // 2

            svg_parts.append(f'  <!-- Connector Layer {idx} -> {idx+1} -->')
            svg_parts.append(f'  <line x1="350" y1="{y_start}" x2="350" y2="{y_end - 7}" class="connector-line" />')
            svg_parts.append(f'  <polygon points="346,{y_end - 7} 354,{y_end - 7} 350,{y_end}" class="connector-arrow" />')
            if connector_label:
                svg_parts.append(f'  <text x="350" y="{y_mid + 4}" class="connector-text">{connector_label}</text>')

    svg_parts.append('</svg>')
    return "\n".join(svg_parts)


def detect_auth_patterns(parsed):
    """Detect RBAC, ABAC, and ReBAC patterns from parsed source files.

    Scans class names, method names, imports, and route decorators for
    known authorization patterns across all supported languages.

    Args:
        parsed (list[dict]): List of file records.

    Returns:
        dict: Keys:
            - ``"rbac"`` (list[dict]): Role-based access control findings.
            - ``"abac"`` (list[dict]): Attribute/policy-based findings.
            - ``"rebac"`` (list[dict]): Relationship-based access control findings.
            - ``"auth_type"`` (str): Dominant auth type label.
            - ``"auth_frameworks"`` (list[str]): Detected auth libraries.
            - ``"protected_routes"`` (list[str]): Routes with auth guards.
            - ``"public_routes"`` (list[str]): Routes with no auth guard.
            - ``"roles_detected"`` (list[str]): Named roles found in code.
            - ``"policies_detected"`` (list[str]): Named policies found.
    """
    rbac_findings   = []
    abac_findings   = []
    rebac_findings  = []
    auth_frameworks = []
    protected_routes = []
    public_routes    = []
    roles_detected   = set()
    policies_detected = set()

    # Pattern libraries per type
    _RBAC_PATTERNS = [
        (r'\[Authorize\s*\(\s*Roles\s*=\s*"([^"]+)"',         "C# Roles attribute"),
        (r'@PreAuthorize\s*\(\s*"hasRole\(\'([^\']+)\'\)',      "Spring @PreAuthorize hasRole"),
        (r'@Secured\s*\(\s*\{\s*"ROLE_([^"]+)"',               "Spring @Secured"),
        (r'User\.IsInRole\s*\(\s*"([^"]+)"',                   "ASP.NET IsInRole check"),
        (r'ClaimTypes\.Role',                                   "ASP.NET ClaimTypes.Role"),
        (r'@login_required',                                    "Django/Flask @login_required"),
        (r'@role_required\s*\(\s*[\'"]([^\'"]+)[\'"]',         "Python role_required"),
        (r'@admin_required',                                    "Flask @admin_required"),
        (r'hasRole\s*\(\s*[\'"]([^\'"]+)[\'"]',                "JS/TS hasRole()"),
        (r'isAdmin\s*\(\)',                                     "isAdmin() check"),
        (r'user\.roles',                                        "user.roles access"),
        (r'req\.user\.role',                                    "Express req.user.role check"),
        (r'RoleHierarchy',                                      "Spring RoleHierarchy"),
        (r'@roles_required',                                    "Flask-Principal @roles_required"),
        (r'@permission_required\s*\(',                         "Django permission_required"),
        (r'IdentityRole',                                       "ASP.NET Identity IdentityRole"),
    ]

    _ABAC_PATTERNS = [
        (r'\[Authorize\s*\(\s*Policy\s*=\s*"([^"]+)"',         "C# Policy attribute"),
        (r'IAuthorizationRequirement',                          "ASP.NET IAuthorizationRequirement"),
        (r'AuthorizationPolicyBuilder',                         "ASP.NET PolicyBuilder"),
        (r'ClaimTypes\.\w+',                                    "ASP.NET Claim attribute check"),
        (r'@PreAuthorize\s*\(\s*"hasPermission\(',              "Spring hasPermission ABAC"),
        (r'@PostAuthorize\s*\(',                                "Spring @PostAuthorize"),
        (r'services\.AddAuthorization',                         "ASP.NET AddAuthorization (policy reg)"),
        (r'RequireAssertion\s*\(',                              "ASP.NET RequireAssertion"),
        (r'ObjectPermission',                                   "Django ObjectPermission"),
        (r'@requires_permission\s*\(',                          "Python requires_permission"),
        (r'PermissionRequiredMixin',                            "Django PermissionRequiredMixin"),
        (r'guardClaims\s*\(',                                   "Claim guard"),
        (r'ResourceFilter',                                     "Resource-level filter"),
    ]

    _REBAC_PATTERNS = [
        (r'IsOwner\s*\(',                                       "IsOwner() relationship check"),
        (r'OwnedBy\s*\(',                                       "OwnedBy relationship check"),
        (r'CreatedBy\s*==',                                     "CreatedBy owner comparison"),
        (r'\.UserId\s*==\s*currentUser',                        "UserId == currentUser comparison"),
        (r'userHasAccess\w*\s*\(',                              "userHasAccess() check"),
        (r'canView\w*\s*\(',                                    "canView() relationship check"),
        (r'canEdit\w*\s*\(',                                    "canEdit() relationship check"),
        (r'CanAccess\s*\(',                                     "CanAccess() check"),
        (r'resourceOwner',                                      "resourceOwner reference"),
        (r'relation\s*=\s*[\'"]owner[\'"]',                    "Zanzibar-style owner relation"),
        (r'CheckAccessAsync\s*\(',                              "CheckAccessAsync (ReBAC-style)"),
        (r'HasPermissionOnResource\s*\(',                       "HasPermissionOnResource check"),
    ]

    _AUTH_FRAMEWORK_PATTERNS = [
        (r'IdentityServer',         "IdentityServer4 / Duende"),
        (r'Keycloak',               "Keycloak"),
        (r'Auth0',                  "Auth0"),
        (r'Okta',                   "Okta"),
        (r'jwt|JwtBearer|JwtSecurityToken', "JWT Bearer Tokens"),
        (r'OAuth',                  "OAuth 2.0"),
        (r'OpenIdConnect|OpenID',   "OpenID Connect"),
        (r'SAML',                   "SAML"),
        (r'Microsoft\.Identity',    "Microsoft Identity Platform"),
        (r'AspNetCore\.Identity',   "ASP.NET Core Identity"),
        (r'Flask-Login|flask_login', "Flask-Login"),
        (r'django\.contrib\.auth',  "Django Auth"),
        (r'passport\b',             "Passport.js"),
        (r'jsonwebtoken',           "jsonwebtoken (Node)"),
        (r'spring-security',        "Spring Security"),
    ]

    _ROLE_VALUE_RE  = re.compile(r'[Rr]oles?\s*=\s*[\'"]([^\'"]+)[\'"]')
    _POLICY_RE      = re.compile(r'[Pp]olicy\s*=\s*[\'"]([^\'"]+)[\'"]')

    for item in parsed:
        content = item.get("content", "") or ""
        file_name = Path(item.get("file", "unknown")).name

        # Detect frameworks
        for pattern, label in _AUTH_FRAMEWORK_PATTERNS:
            if re.search(pattern, content) and label not in auth_frameworks:
                auth_frameworks.append(label)

        # Extract named roles from content
        for m in _ROLE_VALUE_RE.finditer(content):
            for role in m.group(1).split(","):
                roles_detected.add(role.strip())

        # Extract named policies
        for m in _POLICY_RE.finditer(content):
            policies_detected.add(m.group(1).strip())

        # Check RBAC patterns
        for pattern, label in _RBAC_PATTERNS:
            matches = re.findall(pattern, content)
            if matches:
                snippet = str(matches[0])[:60] if matches else ""
                rbac_findings.append({
                    "file": file_name,
                    "pattern": label,
                    "example": snippet,
                })

        # Check ABAC patterns
        for pattern, label in _ABAC_PATTERNS:
            if re.search(pattern, content):
                abac_findings.append({
                    "file": file_name,
                    "pattern": label,
                    "example": "",
                })

        # Check ReBAC patterns
        for pattern, label in _REBAC_PATTERNS:
            if re.search(pattern, content):
                rebac_findings.append({
                    "file": file_name,
                    "pattern": label,
                    "example": "",
                })

        # Tag routes as protected or public
        for route in item.get("routes", []):
            path = route.get("path", "")
            has_auth = (
                re.search(r'\[Authorize', content) or
                re.search(r'@login_required', content) or
                re.search(r'@PreAuthorize', content) or
                re.search(r'@Secured', content) or
                re.search(r'canActivate', content) or
                re.search(r'AuthGuard', content)
            )
            if has_auth:
                protected_routes.append(path)
            else:
                public_routes.append(path)

    # Deduplicate
    def _dedup(findings):
        seen = set()
        out  = []
        for f in findings:
            key = (f["file"], f["pattern"])
            if key not in seen:
                seen.add(key)
                out.append(f)
        return out

    rbac_findings  = _dedup(rbac_findings)[:20]
    abac_findings  = _dedup(abac_findings)[:20]
    rebac_findings = _dedup(rebac_findings)[:20]

    # Determine dominant auth type
    counts = {
        "RBAC (Role-Based)": len(rbac_findings),
        "ABAC (Policy/Attribute-Based)": len(abac_findings),
        "ReBAC (Relationship-Based)": len(rebac_findings),
    }
    if not any(counts.values()):
        auth_type = "No structured authorization detected"
    elif counts["RBAC (Role-Based)"] >= counts["ABAC (Policy/Attribute-Based)"] and \
         counts["RBAC (Role-Based)"] >= counts["ReBAC (Relationship-Based)"]:
        auth_type = "RBAC (Role-Based Access Control)"
    elif counts["ABAC (Policy/Attribute-Based)"] >= counts["ReBAC (Relationship-Based)"]:
        if counts["RBAC (Role-Based)"] > 0:
            auth_type = "Hybrid RBAC + ABAC"
        else:
            auth_type = "ABAC (Attribute/Policy-Based Access Control)"
    else:
        auth_type = "ReBAC (Relationship-Based Access Control)"

    # Add ABAC+ReBAC combo label
    if rebac_findings and abac_findings and rbac_findings:
        auth_type = "Hybrid RBAC + ABAC + ReBAC"
    elif rebac_findings and rbac_findings:
        auth_type = "Hybrid RBAC + ReBAC"

    return {
        "rbac":               rbac_findings,
        "abac":               abac_findings,
        "rebac":              rebac_findings,
        "auth_type":          auth_type,
        "auth_frameworks":    list(dict.fromkeys(auth_frameworks)),
        "protected_routes":   list(dict.fromkeys(protected_routes))[:30],
        "public_routes":      list(dict.fromkeys(public_routes))[:30],
        "roles_detected":     sorted(roles_detected),
        "policies_detected":  sorted(policies_detected),
    }


def detect_screens_navigation(parsed, endpoints):
    """Detect web screens/pages and infer end-to-end navigation flow.

    Identifies individual pages or views from file paths (.aspx, Razor views,
    React/Vue components, Django templates, JSP pages) and maps navigation
    paths between them based on routing configurations and link patterns.

    Args:
        parsed (list[dict]): List of file records from parse_file().
        endpoints (list[dict]): API endpoint records.

    Returns:
        dict: Keys:
            - ``"screens"`` (list[dict]): Each screen with name, path, type,
              methods, description.
            - ``"navigation_flow"`` (list[dict]): Inferred navigation edges.
            - ``"screen_count"`` (int): Total screens detected.
            - ``"project_type"`` (str): e.g. "ASP.NET Web Forms", "MVC", "SPA".
    """
    screens = []
    nav_flow = []
    seen_screens = set()

    # Screen detection by file extension and path
    _SCREEN_PATTERNS = [
        # ASP.NET Web Forms
        (r'\.aspx$',           "ASP.NET Web Forms Page"),
        (r'\.aspx\.cs$',       "ASP.NET Web Forms Code-Behind"),
        # ASP.NET MVC / Razor Pages
        (r'\.cshtml$',         "Razor View / Page"),
        (r'\.vbhtml$',         "Razor VB View"),
        # Java Server Pages / Thymeleaf
        (r'\.jsp$',            "Java Server Page (JSP)"),
        (r'\.jspx$',           "JSPX Page"),
        (r'\.html$',           "HTML Template"),
        # Python templates
        (r'\.html$',           "Django/Jinja2 Template"),
        # React / Vue / Angular
        (r'\.tsx$',            "React/TypeScript Component"),
        (r'\.jsx$',            "React Component"),
        (r'\.vue$',            "Vue Single-File Component"),
        # Angular
        (r'\.component\.ts$',  "Angular Component"),
        (r'\.component\.html$',"Angular Template"),
    ]

    # Route → page type from controller names
    _CTRL_PAGE_HINTS = {
        "home":       "Home / Landing Page",
        "login":      "Login Screen",
        "logout":     "Logout Handler",
        "register":   "Registration Page",
        "signup":     "Sign-Up Screen",
        "dashboard":  "Dashboard / Overview",
        "profile":    "User Profile Page",
        "settings":   "Settings Screen",
        "admin":      "Admin Panel / Back-Office",
        "catalog":    "Product Catalog",
        "product":    "Product Detail Page",
        "cart":       "Shopping Cart",
        "checkout":   "Checkout Screen",
        "order":      "Order Summary / History",
        "payment":    "Payment Screen",
        "search":     "Search Results Page",
        "report":     "Reports / Analytics Screen",
        "user":       "User Management Screen",
        "account":    "Account Page",
        "error":      "Error Page",
        "notfound":   "404 Not Found Page",
        "contact":    "Contact Page",
        "about":      "About / Info Page",
        "help":       "Help / FAQ Page",
    }

    # 1. Detect screens from file paths
    for item in parsed:
        file_path = item.get("file", "")
        file_lower = file_path.lower().replace("\\", "/")
        name = Path(file_path).name
        stem = Path(file_path).stem
        # Remove .aspx from stem for code-behind files like Login.aspx.cs
        if stem.lower().endswith(".aspx"):
            stem = stem[:-5]

        screen_type = None
        for pattern, stype in _SCREEN_PATTERNS:
            if re.search(pattern, file_lower):
                screen_type = stype
                break

        if screen_type and stem not in seen_screens:
            seen_screens.add(stem)
            # Get routes defined in this file
            file_routes = [r.get("path", "/") for r in item.get("routes", [])]
            # Infer description from stem keywords
            stem_lower = stem.lower()
            description = next(
                (desc for kw, desc in _CTRL_PAGE_HINTS.items() if kw in stem_lower),
                f"{stem} Screen"
            )
            screens.append({
                "name":        stem,
                "file":        name,
                "type":        screen_type,
                "routes":      file_routes[:5],
                "description": description,
                "classes":     item.get("classes", [])[:3],
            })

    # 2. Extract screens from MVC controller endpoints (when no view files exist)
    if len(screens) < 5 and endpoints:
        ep_groups: dict = {}
        for ep in endpoints:
            parts = [
                p for p in ep["path"].split("/")
                if p and not p.startswith("{") and
                p.lower() not in ("api", "v1", "v2", "v3", "rest")
            ]
            if parts:
                controller = parts[0].lower()
                action     = parts[1].lower() if len(parts) > 1 else "index"
                ep_groups.setdefault(controller, []).append({
                    "action":  action,
                    "path":    ep["path"],
                    "methods": ep.get("methods", ["GET"]),
                })

        for ctrl, actions in list(ep_groups.items())[:20]:
            if ctrl not in seen_screens:
                seen_screens.add(ctrl)
                description = next(
                    (desc for kw, desc in _CTRL_PAGE_HINTS.items() if kw in ctrl),
                    f"{ctrl.title()} Screen"
                )
                screens.append({
                    "name":        ctrl.title(),
                    "file":        f"{ctrl}_controller",
                    "type":        "MVC Controller Actions",
                    "routes":      [a["path"] for a in actions[:5]],
                    "description": description,
                    "classes":     [],
                })

    # 3. Infer navigation flow from common screen adjacencies
    _NAV_EDGES = [
        ("login",    "dashboard",  "On successful login"),
        ("login",    "register",   "Sign up link"),
        ("register", "login",      "After registration"),
        ("home",     "login",      "Login button"),
        ("home",     "catalog",    "Browse products"),
        ("home",     "search",     "Search bar"),
        ("catalog",  "product",    "Select product"),
        ("product",  "cart",       "Add to cart"),
        ("cart",     "checkout",   "Proceed to checkout"),
        ("checkout", "payment",    "Enter payment"),
        ("payment",  "order",      "Order confirmation"),
        ("order",    "dashboard",  "Continue shopping"),
        ("dashboard","profile",    "View profile"),
        ("dashboard","settings",   "Settings link"),
        ("dashboard","report",     "View reports"),
        ("admin",    "user",       "Manage users"),
        ("admin",    "report",     "View analytics"),
    ]

    screen_names_lower = {s["name"].lower(): s["name"] for s in screens}
    for src_kw, tgt_kw, label in _NAV_EDGES:
        src = next((n for k, n in screen_names_lower.items() if src_kw in k), None)
        tgt = next((n for k, n in screen_names_lower.items() if tgt_kw in k), None)
        if src and tgt and src != tgt:
            nav_flow.append({"from": src, "to": tgt, "label": label})

    # Deduplicate nav flow
    seen_edges = set()
    unique_flow = []
    for edge in nav_flow:
        key = (edge["from"], edge["to"])
        if key not in seen_edges:
            seen_edges.add(key)
            unique_flow.append(edge)

    # Determine project type
    exts = " ".join(item.get("file", "") for item in parsed).lower()
    if ".aspx" in exts:
        project_type = "ASP.NET Web Forms"
    elif ".cshtml" in exts:
        project_type = "ASP.NET MVC / Razor Pages"
    elif ".jsx" in exts or ".tsx" in exts:
        project_type = "React Single-Page Application"
    elif ".vue" in exts:
        project_type = "Vue.js Application"
    elif "component.ts" in exts:
        project_type = "Angular Application"
    elif ".jsp" in exts:
        project_type = "Java Web Application (JSP)"
    elif endpoints:
        project_type = "API-Driven Web Application (MVC)"
    else:
        project_type = "Web Application"

    return {
        "screens":       screens[:40],
        "navigation_flow": unique_flow[:30],
        "screen_count":  len(screens),
        "project_type":  project_type,
    }


def generate_dep_graph_svg(dep_graph_data):
    """Generate an SVG dependency graph using a hierarchical column layout.

    Nodes are classified by their edge connectivity and placed in columns:
    - Sources  (only outgoing edges) → left column
    - Hubs     (both in and out)     → centre column
    - Sinks    (only incoming edges) → right column
    - Isolated (no edges)            → compact grid at bottom

    This approach produces a clear, readable left-to-right dependency flow
    regardless of graph sparsity, avoiding the "all-nodes-pile-at-bottom"
    problem that force-directed algorithms produce on sparse graphs.

    Args:
        dep_graph_data (dict): Dependency graph with "nodes" and "edges" lists.

    Returns:
        str: Self-contained XML SVG content.
    """
    if not dep_graph_data or "nodes" not in dep_graph_data:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="50"><text x="10" y="30">No graph generated</text></svg>'

    nodes = dep_graph_data.get("nodes", [])
    edges = dep_graph_data.get("edges", [])

    if not nodes:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="50"><text x="10" y="30">No nodes in graph</text></svg>'

    import math

    # ---------------------------------------------------------------
    # 1. Classify nodes by connectivity
    # ---------------------------------------------------------------
    out_deg: dict = {n["id"]: 0 for n in nodes}
    in_deg:  dict = {n["id"]: 0 for n in nodes}
    for e in edges:
        if e["from"] in out_deg:
            out_deg[e["from"]] += 1
        if e["to"] in in_deg:
            in_deg[e["to"]] += 1

    sources, hubs, sinks, isolated = [], [], [], []
    for n in nodes:
        nid = n["id"]
        _o, _i = out_deg.get(nid, 0), in_deg.get(nid, 0)
        if _o > 0 and _i == 0:
            sources.append(n)
        elif _o > 0 and _i > 0:
            hubs.append(n)
        elif _i > 0 and _o == 0:
            sinks.append(n)
        else:
            isolated.append(n)

    # Sort columns by connectivity (most connected first)
    sources.sort(key=lambda n: out_deg.get(n["id"], 0), reverse=True)
    hubs.sort(key=lambda n: out_deg.get(n["id"], 0) + in_deg.get(n["id"], 0), reverse=True)
    sinks.sort(key=lambda n: in_deg.get(n["id"], 0), reverse=True)

    # ---------------------------------------------------------------
    # 2. Layout constants
    # ---------------------------------------------------------------
    SVG_W      = 800
    PILL_H     = 26
    ROW_STEP   = 42         # vertical distance between node centres in column
    TOP_MARGIN = 60         # space for title + legend
    COL_PAD    = 20         # horizontal padding inside column zone

    # Three-column x-centre positions
    COL_X = {
        "source": 133,
        "hub":    400,
        "sink":   667,
    }

    # ---------------------------------------------------------------
    # 3. Node → (x, y) positions
    # ---------------------------------------------------------------
    pos: dict = {}          # node_id → [cx, cy]
    max_rows = max(len(sources), len(hubs), len(sinks), 1)
    col_height = TOP_MARGIN + max_rows * ROW_STEP + 20

    def _place_col(col_nodes, cx):
        total = len(col_nodes)
        start_y = TOP_MARGIN + (max_rows - total) * ROW_STEP // 2 + ROW_STEP // 2
        for i, n in enumerate(col_nodes):
            pos[n["id"]] = [cx, start_y + i * ROW_STEP]

    _place_col(sources,  COL_X["source"])
    _place_col(hubs,     COL_X["hub"])
    _place_col(sinks,    COL_X["sink"])

    # Isolated nodes go into a compact grid at the bottom
    GRID_COLS      = 5
    ISO_PILL_W     = 130
    ISO_PILL_H     = 22
    ISO_H_STEP     = 34
    ISO_W_STEP     = 148
    ISO_TOP        = col_height + 24
    ISO_LEFT_START = (SVG_W - min(len(isolated), GRID_COLS) * ISO_W_STEP) // 2 + ISO_PILL_W // 2

    for i, n in enumerate(isolated):
        col_i = i % GRID_COLS
        row_i = i // GRID_COLS
        pos[n["id"]] = [ISO_LEFT_START + col_i * ISO_W_STEP, ISO_TOP + row_i * ISO_H_STEP]

    iso_rows  = math.ceil(len(isolated) / GRID_COLS) if isolated else 0
    iso_block = iso_rows * ISO_H_STEP + (30 if isolated else 0)
    SVG_H     = ISO_TOP + iso_block + 20

    # ---------------------------------------------------------------
    # 4. Label helpers
    # ---------------------------------------------------------------
    MAX_LBL = 22

    def _trunc(lbl):
        return lbl if len(lbl) <= MAX_LBL else lbl[:MAX_LBL - 1] + "…"

    def _pill_w(lbl):
        return max(80, min(190, len(lbl) * 7 + 20))

    def _node_color(lbl):
        ll = lbl.lower()
        if "controller" in ll or "handler" in ll:
            return "#0071e3", "#005bb5", "#ffffff"
        if "service" in ll or "manager" in ll:
            return "#30d158", "#1a8c3a", "#ffffff"
        if "repository" in ll or "repo" in ll or "context" in ll:
            return "#ff9f0a", "#c47900", "#ffffff"
        if "entity" in ll or "model" in ll or "domain" in ll:
            return "#af52de", "#7a22b8", "#ffffff"
        return "#f0f0f5", "#c7c7cc", "#1d1d1f"

    # ---------------------------------------------------------------
    # 5. SVG assembly
    # ---------------------------------------------------------------
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_W}" height="{SVG_H}" viewBox="0 0 {SVG_W} {SVG_H}">',
        '  <defs>',
        '    <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5"',
        '            markerWidth="5" markerHeight="5" orient="auto">',
        '      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#8e8e93"/>',
        '    </marker>',
        '  </defs>',
        f'  <rect width="{SVG_W}" height="{SVG_H}" fill="#fafafa" rx="12" stroke="#e5e5ea" stroke-width="1"/>',
        '  <style>',
        '    .g-title { font: 700 14px -apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif; fill:#1d1d1f; }',
        '    .g-col   { font: 700 10px -apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif; fill:#8e8e93; letter-spacing:.6px; }',
        '    .g-sep   { fill: none; stroke: #e5e5ea; stroke-width: 1; stroke-dasharray: 4 4; }',
        '    .g-lbl   { font: 600 10px -apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif; text-anchor:middle; dominant-baseline:middle; }',
        '    .g-iso   { font: 500 9px -apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif; text-anchor:middle; dominant-baseline:middle; fill:#6e6e73; }',
        '    .g-edge  { stroke:#c7c7cc; stroke-width:1.5; fill:none; marker-end:url(#arr); }',
        '  </style>',
        # Title
        '  <text x="24" y="28" class="g-title">Module Dependency Graph</text>',
    ]

    # Column header labels (only when that column has nodes)
    col_headers = [
        (COL_X["source"], "SOURCES",  len(sources)),
        (COL_X["hub"],    "HUBS",     len(hubs)),
        (COL_X["sink"],   "TARGETS",  len(sinks)),
    ]
    for cx, lbl, cnt in col_headers:
        if cnt:
            parts.append(f'  <text x="{cx}" y="46" class="g-col" text-anchor="middle">{lbl} ({cnt})</text>')

    # Vertical separator lines between columns
    if len(sources) or len(hubs) or len(sinks):
        for sx in [267, 533]:
            parts.append(f'  <line x1="{sx}" y1="{TOP_MARGIN - 8}" x2="{sx}" y2="{col_height}" class="g-sep"/>')

    # ----------- Draw edges (bezier curves between pill boundaries) -----------
    for e in edges:
        uid, vid = e["from"], e["to"]
        if uid not in pos or vid not in pos:
            continue
        ux, uy = pos[uid]
        vx, vy = pos[vid]

        u_lbl = next((n.get("label","") for n in nodes if n["id"] == uid), "")
        v_lbl = next((n.get("label","") for n in nodes if n["id"] == vid), "")
        uw = _pill_w(_trunc(u_lbl)) / 2
        vw = _pill_w(_trunc(v_lbl)) / 2

        # Start from right edge of source pill, end at left edge of target pill
        x1 = ux + uw
        y1 = uy
        x2 = vx - vw - 6   # leave 6px gap for arrowhead
        y2 = vy
        cp_x = (x1 + x2) / 2
        parts.append(f'  <path d="M {x1:.0f},{y1:.0f} C {cp_x:.0f},{y1:.0f} {cp_x:.0f},{y2:.0f} {x2:.0f},{y2:.0f}" class="g-edge"/>')

    # ----------- Draw connected node pills -----------
    for col_nodes in (sources, hubs, sinks):
        for n in col_nodes:
            nid = n["id"]
            lbl_full = n.get("label", "")
            lbl = _trunc(lbl_full)
            cx, cy = pos[nid]
            w = _pill_w(lbl)
            fill, stroke, font_c = _node_color(lbl_full)
            rx_pill = cx - w / 2
            ry_pill = cy - PILL_H / 2
            parts.append(f'  <rect x="{rx_pill:.0f}" y="{ry_pill:.0f}" width="{w}" height="{PILL_H}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
            parts.append(f'  <text x="{cx:.0f}" y="{cy + 1:.0f}" fill="{font_c}" class="g-lbl">{lbl}</text>')

    # ----------- Isolated grid -----------
    if isolated:
        parts.append(f'  <text x="24" y="{ISO_TOP - 10}" class="g-col">ALL MODULES ({len(isolated)})</text>')
        for n in isolated:
            nid = n["id"]
            lbl_full = n.get("label", "")
            lbl = _trunc(lbl_full)
            cx, cy = pos[nid]
            w = ISO_PILL_W
            fill, stroke, font_c = _node_color(lbl_full)
            # Isolated nodes use a lighter style (no color fill unless role-named)
            if fill == "#f0f0f5":
                fill, stroke, font_c = "#ffffff", "#d1d1d6", "#6e6e73"
            rx_pill = cx - w / 2
            ry_pill = cy - ISO_PILL_H / 2
            parts.append(f'  <rect x="{rx_pill:.0f}" y="{ry_pill:.0f}" width="{w}" height="{ISO_PILL_H}" rx="5" fill="{fill}" stroke="{stroke}" stroke-width="1"/>')
            parts.append(f'  <text x="{cx:.0f}" y="{cy + 1:.0f}" fill="{font_c}" class="g-iso">{lbl}</text>')

    parts.append('</svg>')
    return "\n".join(parts)

