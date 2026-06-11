# spec-governance — file reference

| Path | What it is | How it works |
|------|-----------|--------------|
| `SKILL.md` | Manifest (YAML frontmatter) + agent instructions | Parsed by the registry; frontmatter drives the MCP tool schema, body guides the agent. |
| `manifest.yaml` | Machine-readable mirror of the manifest | Convenience for external tooling; the registry reads `SKILL.md`. |
| `scripts/main.py` | Entrypoint exposing `run(inputs) -> dict` | Called in an isolated subprocess; inputs are pre-validated. |
| `scripts/__init__.py` | Marks `scripts/` importable | Lets the entrypoint import siblings. |
| `references/` | Background docs | Human reference; not executed. |
| `templates/` | Output templates | Patterns the script fills in. |
| `tests/` | Skill-local smoke tests | Run with pytest against `run()`. |
| `DOCS.md` | This file | Explains every file. |
