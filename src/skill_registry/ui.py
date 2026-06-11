"""Apple-styled Gradio upload UI, mounted into the FastAPI app at ``/ui``.

Lets a user upload a skill as a ZIP, validate that it matches the required
format, and on success install it and (when configured) auto-commit it to the
GitHub ``skills/`` folder — which redeploys the Space.
"""

from __future__ import annotations

from skill_registry.config import Settings
from skill_registry.services import SkillRegistry

_APPLE_CSS = """
:root { --bg:#f5f5f7; --card:#ffffff; --ink:#1d1d1f; --muted:#6e6e73; --accent:#0071e3; }
.gradio-container {
  background: var(--bg) !important;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif !important;
  color: var(--ink) !important;
  max-width: 880px !important; margin: 0 auto !important;
}
#hero { text-align:center; padding: 36px 0 8px; }
#hero h1 { font-size: 40px; font-weight: 700; letter-spacing:-.02em; margin:0; }
#hero p { color: var(--muted); font-size: 18px; margin-top: 8px; }
.card {
  background: var(--card) !important; border:none !important;
  border-radius: 18px !important; padding: 22px !important;
  box-shadow: 0 4px 24px rgba(0,0,0,.06) !important; margin-bottom: 18px !important;
}
button.primary, .primary button {
  background: var(--accent) !important; border:none !important;
  border-radius: 980px !important; font-weight: 600 !important; color:#fff !important;
}
button { border-radius: 980px !important; }
footer { display:none !important; }
.result-ok   { color:#1d7d33; }
.result-err  { color:#c0392b; }
"""

_FORMAT_HELP = """
### Required format

```
skill-name/
├── SKILL.md          # required — YAML frontmatter + instructions
├── scripts/          # optional — entrypoint exposes run(inputs) -> dict
├── references/       # optional
└── assets/           # optional
```

`SKILL.md` frontmatter must include at least **`name`** (lowercase slug) and
**`description`**. Zip the `skill-name/` folder and upload it below.
"""


def _manifest_card(manifest) -> str:
    inputs = ", ".join(f"`{p.name}`" for p in manifest.inputs) or "—"
    outputs = ", ".join(f"`{p.name}`" for p in manifest.outputs) or "—"
    tags = " ".join(f"`{t}`" for t in manifest.tags) or "—"
    return (
        f"### ✅ Valid — `{manifest.name}` v{manifest.version}\n\n"
        f"{manifest.description}\n\n"
        f"- **Category:** {manifest.category}\n"
        f"- **Tags:** {tags}\n"
        f"- **Inputs:** {inputs}\n"
        f"- **Outputs:** {outputs}\n"
        f"- **Entrypoint:** `{manifest.execution.entrypoint}`"
    )


def build_ui(registry: SkillRegistry, settings: Settings):
    """Construct the Gradio Blocks app. Imports gradio lazily."""
    import gradio as gr

    def validate(file_bytes: bytes | None) -> str:
        if not file_bytes:
            return "<span class='result-err'>Please choose a `.zip` file first.</span>"
        try:
            manifest = registry.validate_upload(file_bytes)
        except Exception as exc:  # noqa: BLE001 - surface any validation error to the user
            return f"<span class='result-err'>❌ Invalid skill: {exc}</span>"
        return _manifest_card(manifest)

    def publish(file_bytes: bytes | None, overwrite: bool) -> str:
        if not file_bytes:
            return "<span class='result-err'>Please choose a `.zip` file first.</span>"
        try:
            result = registry.install_and_publish(file_bytes, overwrite=overwrite)
        except Exception as exc:  # noqa: BLE001
            return f"<span class='result-err'>❌ Upload failed: {exc}</span>"

        manifest = result["manifest"]
        url = result["github_url"]
        lines = [f"### 🎉 `{manifest.name}` v{manifest.version} is live"]
        lines.append("Installed and available now via the MCP and REST APIs.")
        if url:
            lines.append(f"Committed to GitHub → [{url}]({url}) (Space will redeploy).")
        elif settings.github_publish_enabled:
            lines.append("_GitHub publish was attempted._")
        else:
            lines.append(
                "_GitHub auto-publish is not configured, so this install is local "
                "to the running server. Set a GitHub token to persist it to the repo._"
            )
        return "\n\n".join(lines)

    with gr.Blocks(css=_APPLE_CSS, theme=gr.themes.Soft(), title="Skill Registry") as demo:
        gr.HTML(
            "<div id='hero'><h1>🧩 Skill Registry</h1>"
            "<p>Upload a skill. We validate the format, install it, and publish it.</p></div>"
        )
        with gr.Column(elem_classes="card"):
            gr.Markdown(_FORMAT_HELP)
        with gr.Column(elem_classes="card"):
            file_in = gr.File(label="Skill .zip", file_types=[".zip"], type="binary")
            overwrite = gr.Checkbox(label="Overwrite if a skill with the same name exists")
            with gr.Row():
                validate_btn = gr.Button("Validate", variant="secondary")
                publish_btn = gr.Button("Upload & Publish", variant="primary")
            output = gr.Markdown()

        validate_btn.click(validate, inputs=file_in, outputs=output)
        publish_btn.click(publish, inputs=[file_in, overwrite], outputs=output)

    return demo
