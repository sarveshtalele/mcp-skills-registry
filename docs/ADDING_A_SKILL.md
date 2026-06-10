# Adding a Skill

A skill is a self-contained folder under `skills/`. The server discovers it at
startup by reading its `SKILL.md`. No server code changes are required.

## 1. Scaffold

```bash
python scripts/new_skill.py my-skill
```

This copies `skills/_template` to `skills/my-skill` and sets the name. Structure:

```
skills/my-skill/
├── SKILL.md              # manifest (YAML frontmatter) + agent instructions
├── scripts/
│   ├── __init__.py
│   └── main.py           # run(inputs: dict) -> dict
├── references/           # optional supporting docs
├── templates/            # optional output templates
└── assets/
    └── requirements.txt  # optional extra pip deps
```

## 2. Fill in `SKILL.md`

The YAML frontmatter (between `---` markers) is the manifest.

```yaml
---
name: my-skill                 # required: lowercase slug (a-z, 0-9, hyphen)
version: 1.0.0                 # semver
description: >                 # required: what it does + trigger phrases
  ...
author: your-handle
license: MIT
category: text-processing
tags: [example]
execution:
  type: python-script          # python-script (runnable) | prompt-based
  entrypoint: scripts/main.py:run
  timeout_seconds: 30          # 1–600, clamped by server policy
inputs:
  - name: text                 # must be a valid identifier
    type: string               # string|integer|number|boolean|array|object
    required: true
    description: ...
    enum: [a, b]               # optional allowed values
outputs:
  - name: result
    type: string
    description: ...
status: active                 # active|beta|deprecated|archived
---
```

The markdown **body** after the frontmatter is free-form agent instructions
(preserved by the loader for reference).

## 3. Implement `scripts/main.py`

Expose `run(inputs: dict) -> dict`. Inputs are already validated against the
manifest; return a JSON-serializable dict matching your declared outputs.

```python
def run(inputs: dict) -> dict:
    text = inputs["text"]
    return {"result": text.upper()}
```

Raise an exception to signal failure — the registry reports it to the caller.

### Rules the executor enforces

- Runs in an isolated subprocess with the declared timeout.
- Must return a `dict`; anything else is an error.
- Output is capped (`SKILLREG_MAX_OUTPUT_BYTES`, default 1 MB).
- Sibling files (`scripts/engine/*.py`, etc.) are importable from the entrypoint.

## 4. Dependencies

List extra pip packages in `assets/requirements.txt`. Add them to the server
image (root `requirements.txt` or the Dockerfile) so they are installed where the
skill runs. Prefer the standard library when possible.

## 5. Load and test

```bash
# Reload the running server's catalogue:
curl -X POST http://localhost:7860/api/v1/admin/reload

# Execute it:
curl -X POST http://localhost:7860/api/v1/skills/my-skill/execute \
  -H 'Content-Type: application/json' \
  -d '{"inputs": {"text": "hello"}}'
```

Add a unit test in `tests/` (see `tests/test_executor.py`) and run `make test`.

## 5b. Upload a packaged skill (no Git)

Package the skill folder as a ZIP (must contain `SKILL.md` at the root or one
level deep) and POST it. The skill installs into `skills/<name>/` and is live
immediately — no restart.

```bash
zip -r my-skill.zip my-skill/
curl -X POST http://localhost:7860/api/v1/skills/upload \
  -F 'file=@my-skill.zip'                 # ?overwrite=true to replace an existing skill
```

The installer validates the manifest before writing and rejects unsafe archives
(path traversal / zip-slip, oversized or zip-bomb archives, names starting with
`_`). Disable uploads entirely with `SKILLREG_ENABLE_UPLOADS=false`.

> On Hugging Face Spaces, uploads persist only if the skills directory lives on
> the persistent `/data` mount (set `SKILLREG_SKILLS_DIR=/data/skills`). Skills
> committed to Git are always baked into the image at build time.

## 6. Keep skills versioned in Git

Skills live in this repository alongside the server, but each in its own folder —
self-contained and independently reviewable. Submit a new skill as a pull request
adding a single `skills/<name>/` directory; CI lints and tests it before merge.
