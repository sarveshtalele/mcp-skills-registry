"""
Pipeline
========
Orchestrates the complete reverse engineering pipeline from repository URL
to output files.  **No API keys or LLM accounts required.**

Entry point: :func:`run_pipeline`.

Pipeline stages:

1. **Clone**   — shallow-clone the repository with :func:`clone_repo`.
2. **Load**    — walk source files with :mod:`engine.loaders`.
3. **Parse**   — extract structural elements with :mod:`engine.parsers`
   (smart priority cap for large repos).
4. **Analyze** — compute metrics, dependency graph, API endpoints, dead code,
   and tech stack with :mod:`engine.analyzer`.
5. **Heuristics** — generate executive summary, modernisation roadmap, and
   business logic analysis with :mod:`engine.ai_analysis` using pure static
   heuristics (no API calls).
6. **Generate** — build SDD JSON, HTML dashboard, and Markdown report with
   :mod:`engine.generators`.
7. **Write**   — persist all outputs via :class:`~engine.output_manager.OutputManager`
   and emit a ``manifest.json`` with run metrics.
8. **Cleanup** — remove the temporary clone directory.
"""

import os
import re
import shutil
import subprocess
import tempfile

from engine.loaders     import load_repo
from engine.parsers     import parse_file
from engine.analyzer    import (
    generate_report,
    build_dependency_map,
    generate_dep_graph_data,
    generate_graphviz_dot,
    extract_api_endpoints,
    generate_openapi_spec,
    detect_dead_code,
    detect_tech_stack,
    detect_platform,
    detect_architecture_layers,
    find_top_modules,
    detect_database_schema,
    suggest_microservice_data_boundaries,
    generate_block_diagram,
    generate_block_diagram_dot,
    generate_block_diagram_svg,
    generate_dep_graph_svg,
    detect_auth_patterns,
    detect_screens_navigation,
)
from engine.ai_analysis import (
    ai_executive_summary,
    ai_modernization_roadmap,
    ai_business_logic_analysis,
    ai_all_sections_claude,
)
from engine.generators.sdd       import generate_sdd
from engine.generators.dashboard import generate_html_dashboard
from engine.generators.report    import generate_md_report
from engine.output_manager       import OutputManager
from engine.evaluator            import evaluate_pipeline_output, write_evaluation_md


def clone_repo(url, target_dir):
    """Shallow-clone a GitHub repository to *target_dir*.

    Performs a ``git clone --depth=1`` to minimise network usage and disk
    space.  Raises :exc:`RuntimeError` if the clone fails.

    Args:
        url (str): GitHub repository URL
            (e.g. ``"https://github.com/owner/repo"``).
        target_dir (str): Local filesystem path where the repository will
            be cloned.

    Raises:
        RuntimeError: If ``git clone`` returns a non-zero exit code, with
            the stderr output included in the exception message.
    """
    print(f"  Cloning {url} -> {target_dir}")
    result = subprocess.run(
        ["git", "clone", "--depth=1", url, target_dir],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git clone failed:\n{result.stderr}")
    print("  [ok] Clone complete")


def repo_name_from_url(url):
    """Extract a sanitised repository name from a GitHub URL.

    Strips trailing slashes and ``.git`` suffixes, takes the final path
    segment, then replaces any character that is not alphanumeric, a
    hyphen, or an underscore with ``_``.

    Args:
        url (str): GitHub repository URL.

    Returns:
        str: A filesystem-safe repository name (e.g. ``"nopCommerce"``).
    """
    name = url.rstrip("/").rstrip(".git").split("/")[-1]
    return re.sub(r'[^\w\-]', '_', name)


def run_pipeline(repo_url, mode="heuristic", output_dir=None):
    """Execute the full reverse engineering pipeline for *repo_url*.

    Clones the repository, analyses the source code, generates five output
    files (SDD JSON, HTML dashboard, Markdown report, quality evaluation,
    manifest), and prints a concise progress summary to stdout.

    Args:
        repo_url (str): GitHub repository URL to analyse.
        mode (str): ``"heuristic"`` (default) or ``"ai"`` (requires
            ``ANTHROPIC_API_KEY`` env var and the ``anthropic`` Python SDK).
        output_dir (str | None): Directory to write output files into.
            Defaults to ``{cwd}/{repo_name}/`` (a folder named after the
            repo in the current working directory).  Pass ``"."`` to write
            files directly into the current directory without a subfolder.

    Returns:
        None

    Side effects:
        - Creates ``{output_dir}/{repo_name}/`` (or ``output_dir``) with output files.
        - Prints stage progress and final file paths to stdout.
    """
    print(f"\n{'='*60}")
    print(f"  Reverse Engineer Skill  (API-key-free edition)")
    print(f"  Repository : {repo_url}")
    print(f"{'='*60}\n")

    repo_name = repo_name_from_url(repo_url)
    tmp_dir   = tempfile.mkdtemp(prefix="rev_eng_")
    repo_path = os.path.join(tmp_dir, repo_name)

    try:
        # ----------------------------------------------------------------
        # 1. Clone
        # ----------------------------------------------------------------
        print("[1/8] Cloning repository...")
        clone_repo(repo_url, repo_path)

        # ----------------------------------------------------------------
        # 2. Load files
        # ----------------------------------------------------------------
        print("[2/8] Loading source files...")
        files = load_repo(repo_path)
        print(f"      Found {len(files)} source files")
        if not files:
            print("  [!] No source files found. Check the repository or supported extensions.")
            return

        # ----------------------------------------------------------------
        # 3. Parse (smart cap: prioritise controllers > services > repos)
        # ----------------------------------------------------------------
        print("[3/8] Parsing code structures...")
        FILE_CAP = 300
        if len(files) > FILE_CAP:
            from collections import defaultdict

            def _layer(f):
                """Classify a file into a layer bucket (0=highest priority)."""
                name     = os.path.basename(f["path"]).lower()
                path_low = f["path"].lower().replace("\\", "/")
                if "controller"                            in name: return 0
                if "service"                               in name: return 1
                if "repository" in name or "repo" in name: return 2
                # Domain/entity classes — guaranteed representation for DB schema detection
                if any(s in path_low for s in ["/domain/", "/entities/", "/entity/"]):
                    return 3
                if "model" in name or "dto" in name:       return 4
                return 5

            # Per-layer slot allocation guarantees domain/entity files always appear
            SLOTS = {0: 75, 1: 75, 2: 40, 3: 60, 4: 30, 5: 20}
            buckets = defaultdict(list)
            for f in files:
                buckets[_layer(f)].append(f)
            files = []
            for layer in sorted(SLOTS):
                files.extend(buckets[layer][:SLOTS[layer]])
            files = files[:FILE_CAP]
            print(
                f"      Capped to {len(files)} files "
                f"(layer-balanced: ctrl/svc/repo/domain/model)"
            )

        parsed, skipped = [], 0
        for f in files:
            result = parse_file(f)
            if result:
                parsed.append(result)
            else:
                skipped += 1
        if skipped:
            print(f"      [!] {skipped} files skipped (unsupported extension or parse error)")
        print(f"      Parsed {len(parsed)} / {len(files)} files")

        # ----------------------------------------------------------------
        # 4. Generate report & metrics
        # ----------------------------------------------------------------
        print("[4/8] Generating metrics report...")
        report   = generate_report(parsed)
        dep_map  = build_dependency_map(parsed)
        top_mods = find_top_modules(dep_map)
        dep_graph = generate_dep_graph_data(parsed)
        dep_graph_dot = generate_graphviz_dot(dep_graph)

        # ----------------------------------------------------------------
        # 5. API & dead code
        # ----------------------------------------------------------------
        print("[5/8] Extracting APIs and detecting dead code...")
        endpoints    = extract_api_endpoints(parsed)
        openapi_spec = generate_openapi_spec(endpoints, repo_name)
        dead_code    = detect_dead_code(parsed)
        tech_stack   = detect_tech_stack(parsed, repo_path)
        db_schema    = detect_database_schema(parsed)
        block_diagram_data = generate_block_diagram(parsed, endpoints, db_schema, tech_stack)
        block_diagram_dot = generate_block_diagram_dot(block_diagram_data)
        print(
            f"      {len(endpoints)} API endpoints | "
            f"{len(dead_code['dead_files'])} dead files | "
            f"{len(tech_stack)} tech stack items"
        )
        print(
            f"      {db_schema['entity_count']} data entities | "
            f"{db_schema['relationship_count']} relationships detected"
        )

        # ----------------------------------------------------------------
        # 6. Analysis — heuristic or Claude AI
        # ----------------------------------------------------------------
        if mode == "ai":
            print("[6/8] Running AI analysis via Claude API...")
            ai_result = ai_all_sections_claude(
                parsed, report, endpoints, db_schema, tech_stack, repo_name
            )
            # ai_result is a 3-tuple or None — never unpack directly without length check
            if isinstance(ai_result, tuple) and len(ai_result) == 3:
                summary, modernization, business_logic = ai_result
                print("      [ok] Claude API analysis complete")
            else:
                print("      [!] Claude API call failed — falling back to heuristic analysis")
                mode = "heuristic"

        if mode != "ai":
            print("[6/8] Running static heuristic analysis...")
            summary        = ai_executive_summary(parsed, report, repo_name)
            modernization  = ai_modernization_roadmap(parsed, report, repo_name, tech_stack)
            business_logic = ai_business_logic_analysis(
                parsed, endpoints, db_schema, report, repo_name
            )

        platform_str    = detect_platform(parsed)
        arch_layers     = detect_architecture_layers(parsed)
        data_boundaries = suggest_microservice_data_boundaries(db_schema, modernization)
        auth_analysis   = detect_auth_patterns(parsed)
        screens_nav     = detect_screens_navigation(parsed, endpoints)
        print(
            f"      Pattern: {summary.get('architecture_pattern')} | "
            f"Priority: {summary.get('modernization_priority')} | "
            f"Domain: {business_logic.get('business_domain', 'N/A')}"
        )
        print(
            f"      Auth type: {auth_analysis.get('auth_type', 'N/A')} | "
            f"Screens detected: {screens_nav.get('screen_count', 0)}"
        )

        # ----------------------------------------------------------------
        # 7. Generate & write outputs via OutputManager
        # ----------------------------------------------------------------
        print("[7/8] Generating output files...")
        # Determine output location: use provided output_dir or default to CWD/{repo_name}
        if output_dir:
            om = OutputManager(repo_name, base_dir=output_dir)
        else:
            om = OutputManager(repo_name, base_dir=".")

        # File 1: SDD JSON
        sdd_data = generate_sdd(
            repo_name, repo_url, parsed, report, dep_map, endpoints,
            openapi_spec, dead_code, dep_graph_dot, tech_stack, summary,
            modernization, repo_path,
            db_schema=db_schema,
            data_boundaries=data_boundaries,
            business_logic=business_logic,
            block_diagram=block_diagram_dot,
            auth_analysis=auth_analysis,
            screens_nav=screens_nav,
        )
        sdd_path = om.write_json(f"{repo_name}_sdd.json", sdd_data)
        print(f"      [ok] SDD JSON -> {sdd_path}")

        # File 2: HTML Dashboard
        html_content = generate_html_dashboard(
            repo_name, repo_url, report, endpoints, dead_code,
            tech_stack, summary, modernization, top_mods,
            platform=platform_str,
            arch_layers=arch_layers,
            db_schema=db_schema,
            data_boundaries=data_boundaries,
            business_logic=business_logic,
            block_diagram=block_diagram_data,
            dep_graph=dep_graph,
        )
        html_path = om.write_text(f"{repo_name}_dashboard.html", html_content)
        print(f"      [ok] HTML Dashboard -> {html_path}")

        # File 3: Markdown Report
        md_content = generate_md_report(
            repo_name, repo_url, report, parsed, dep_map, endpoints,
            openapi_spec, dead_code, tech_stack, summary,
            modernization, top_mods,
            db_schema=db_schema,
            data_boundaries=data_boundaries,
            business_logic=business_logic,
            block_diagram=block_diagram_data,
            auth_analysis=auth_analysis,
            screens_nav=screens_nav,
        )
        md_path = om.write_text(f"{repo_name}_report.md", md_content)
        print(f"      [ok] MD Report -> {md_path}")

        # File 4: Block Diagram SVG
        svg_content = generate_block_diagram_svg(block_diagram_data)
        svg_path = om.write_text(f"{repo_name}_block_diagram.svg", svg_content)
        print(f"      [ok] Block Diagram SVG -> {svg_path}")

        # File 5: Dependency Graph SVG
        dep_svg_content = generate_dep_graph_svg(dep_graph)
        dep_svg_path = om.write_text(f"{repo_name}_dependency_graph.svg", dep_svg_content)
        print(f"      [ok] Dependency Graph SVG -> {dep_svg_path}")

        # Manifest
        primary_lang = (
            max(report["languages"], key=report["languages"].get)
            if report["languages"]
            else "unknown"
        )
        om.write_manifest(
            files_analyzed=report["total_files"],
            classes=report["total_classes"],
            methods=report["total_methods"],
            api_endpoints=len(endpoints),
            dead_files=len(dead_code.get("dead_files", [])),
            primary_language=primary_lang,
        )

        # ----------------------------------------------------------------
        # 8. Evaluate pipeline outputs
        # ----------------------------------------------------------------
        print("[8/8] Evaluating pipeline output quality...")
        evaluation = evaluate_pipeline_output(
            parsed=parsed,
            report=report,
            endpoints=endpoints,
            dead_code=dead_code,
            dep_map=dep_map,
            graphviz_code=dep_graph_dot,
            tech_stack=tech_stack,
            summary=summary,
            modernization=modernization,
            db_schema=db_schema,
            data_boundaries=data_boundaries,
            repo_name=repo_name,
        )
        eval_md = write_evaluation_md(evaluation)
        eval_path = om.write_text(f"{repo_name}_evaluation.md", eval_md)
        print(f"      [ok] Evaluation Report -> {eval_path}")

        # ----------------------------------------------------------------
        # 9. Done — print summary
        # ----------------------------------------------------------------
        print("\n[9/9] Complete!\n")
        print(f"{'='*60}")
        print(f"  DONE  {repo_name}")
        print(f"{'='*60}")
        print(f"  Files analyzed : {report['total_files']}  |  Classes : {report['total_classes']}  |  Methods : {report['total_methods']}")
        print(f"  API endpoints  : {len(endpoints)}  |  Dead files : {len(dead_code['dead_files'])}  |  Language : {primary_lang}")
        print(f"  Priority       : {summary.get('modernization_priority', 'N/A')}  |  Domain : {business_logic.get('business_domain', 'N/A')}")
        print(f"\n  Output files:")
        for line in om.summary_lines():
            print(line)
        print(f"\n  Open the .md report or .html dashboard for full analysis details.")
        print(f"{'='*60}\n")

    finally:
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass
