# Skills Catalogue

Each subdirectory here is one **self-contained skill**. The registry server
auto-discovers them at startup by reading each `SKILL.md`. Directories whose name
starts with `_` (such as `_template/`) are ignored.

## Folder structure

This convention mirrors the
[change-impact-analysis-skill](https://github.com/sarveshtalele/change-impact-analysis-skill)
and [reverse-engineering-skill](https://github.com/sarveshtalele/reverse-engineering-skill-github-copilot)
layouts:

```
skills/
└── my-skill/
    ├── SKILL.md              # YAML frontmatter (manifest) + agent instructions
    ├── README.md             # human docs
    ├── scripts/
    │   ├── __init__.py
    │   └── main.py           # exposes run(inputs: dict) -> dict
    ├── references/           # supporting reference docs (optional)
    ├── templates/            # output templates (optional)
    └── assets/
        └── requirements.txt  # extra pip deps for this skill (optional)
```

## The `SKILL.md` manifest

The YAML frontmatter (between the `---` markers) is parsed into a validated
manifest. Required: `name` (lowercase slug), `description`. Recommended fields:
`version` (semver), `category`, `tags`, `execution`, `inputs`, `outputs`.

`execution.entrypoint` points at the callable that runs the skill, in the form
`path/to/file.py:function_name`. That function must accept a single `dict` of
inputs and return a JSON-serializable `dict`.

## Adding a skill

```bash
# Scaffold from the template:
python scripts/new_skill.py my-new-skill

# ...implement scripts/main.py and fill in SKILL.md, then reload:
curl -X POST http://localhost:7860/api/v1/admin/reload
```

See [docs/ADDING_A_SKILL.md](../docs/ADDING_A_SKILL.md) for the full guide.
