# Contributing

## Dev setup

```bash
python -m venv .venv && source .venv/bin/activate
make install        # editable install with dev extras
```

## Before opening a PR

```bash
make format         # ruff --fix + black
make lint           # ruff + black --check
make test           # pytest
```

CI runs the same checks on Python 3.10–3.12.

## Adding a skill

See [docs/ADDING_A_SKILL.md](docs/ADDING_A_SKILL.md). A skill PR should add a
single `skills/<name>/` folder with a valid `SKILL.md`, an entrypoint exposing
`run(inputs) -> dict`, and at least one test.

## Conventions

- Layered architecture: `api → mcp/services → repositories → db → models`. Don't
  reach across layers.
- Type-hint public functions; keep modules small and single-purpose.
- Line length 100; formatting by black; linting by ruff (config in `pyproject.toml`).
