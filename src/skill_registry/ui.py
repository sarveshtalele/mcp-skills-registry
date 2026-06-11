"""Apple-inspired (amber + light) Gradio UI, mounted into the FastAPI app.

Upload a skill ZIP → validate the format → install it and (when configured)
auto-commit it to the GitHub ``skills/`` folder, which redeploys the Space.
"""

from __future__ import annotations

from skill_registry.config import Settings
from skill_registry.services import SkillRegistry

# Warm, amber-accented light theme with Apple-style typography and soft cards.
_THEME_CSS = """
:root {
  --bg1:#fffaf2; --bg2:#fff3df; --card:#ffffff; --ink:#1d1d1f; --muted:#6e6e73;
  --amber:#f59e0b; --amber-d:#d97706; --line:#f0e6d6;
}
.gradio-container {
  background: linear-gradient(180deg, var(--bg2) 0%, var(--bg1) 240px) !important;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif !important;
  color: var(--ink) !important; max-width: 820px !important; margin: 0 auto !important;
}
#hero { text-align:center; padding: 44px 16px 6px; }
#hero .badge {
  display:inline-block; font-size:13px; font-weight:600; color:var(--amber-d);
  background:#fff7ea; border:1px solid var(--line); padding:6px 14px; border-radius:980px; margin-bottom:16px;
}
#hero h1 { font-size:42px; font-weight:700; letter-spacing:-.02em; margin:0;
  background:linear-gradient(90deg,#1d1d1f,#b45309); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
#hero p { color:var(--muted); font-size:18px; margin-top:10px; }
.card {
  background:var(--card) !important; border:1px solid var(--line) !important;
  border-radius:20px !important; padding:24px !important;
  box-shadow:0 8px 30px rgba(180,120,20,.07) !important; margin-bottom:18px !important;
}
.step { font-size:13px; font-weight:700; color:var(--amber-d); letter-spacing:.04em; text-transform:uppercase; }
.gradio-container .primary, .gradio-container .primary button {
  background:linear-gradient(180deg,var(--amber),var(--amber-d)) !important; border:none !important;
  color:#fff !important; font-weight:600 !important; border-radius:980px !important;
  box-shadow:0 4px 14px rgba(245,158,11,.35) !important;
}
.gradio-container button { border-radius:980px !important; font-weight:600 !important; }
.gradio-container .secondary button { background:#fff !important; border:1px solid var(--line) !important; color:var(--ink) !important; }
.result-ok  { color:#15803d; } .result-err { color:#b91c1c; }
footer { display:none !important; }
"""

_FORMAT_HELP = """
<span class="step">Format</span>
A skill is a folder; zip it and upload below.
```
skill-name/
├── SKILL.md          required — YAML frontmatter + instructions
├── scripts/          optional — entrypoint exposes run(inputs) -> dict
├── references/       optional
└── assets/           optional
```
`SKILL.md` frontmatter needs at least **`name`** (lowercase slug) and **`description`**.
"""


def _manifest_card(manifest) -> str:
    inputs = ", ".join(f"`{p.name}`" for p in manifest.inputs) or "—"
    outputs = ", ".join(f"`{p.name}`" for p in manifest.outputs) or "—"
    tags = " ".join(f"`{t}`" for t in manifest.tags) or "—"
    return (
        f"<span class='result-ok'>### ✅ Valid — `{manifest.name}` v{manifest.version}</span>\n\n"
        f"{manifest.description}\n\n"
        f"- **Category:** {manifest.category} &nbsp;•&nbsp; **Tags:** {tags}\n"
        f"- **Inputs:** {inputs}\n- **Outputs:** {outputs}\n"
        f"- **Entrypoint:** `{manifest.execution.entrypoint}`\n\n"
        f"_Looks good — click **Upload & Publish**._"
    )


def build_ui(registry: SkillRegistry, settings: Settings):
    """Construct the Gradio Blocks app. Imports gradio lazily."""
    import gradio as gr

    def validate(file_bytes: bytes | None) -> str:
        if not file_bytes:
            return "<span class='result-err'>Choose a `.zip` file first.</span>"
        try:
            manifest = registry.validate_upload(file_bytes)
        except Exception as exc:  # noqa: BLE001
            return f"<span class='result-err'>❌ Invalid skill — {exc}</span>"
        return _manifest_card(manifest)

    def publish(file_bytes: bytes | None, overwrite: bool) -> str:
        if not file_bytes:
            return "<span class='result-err'>Choose a `.zip` file first.</span>"
        try:
            result = registry.install_and_publish(file_bytes, overwrite=overwrite)
        except Exception as exc:  # noqa: BLE001
            return f"<span class='result-err'>❌ Upload failed — {exc}</span>"
        manifest, url = result["manifest"], result["github_url"]
        out = [
            f"<span class='result-ok'>### 🎉 `{manifest.name}` v{manifest.version} is live</span>"
        ]
        out.append("Available now through the MCP and REST APIs.")
        if url:
            out.append(f"Committed to GitHub → [{url}]({url}). The Space will redeploy.")
        elif not settings.github_publish_enabled:
            out.append(
                "_Installed on this server. Set `SKILLREG_GITHUB_TOKEN` to also commit "
                "it to the repository._"
            )
        return "\n\n".join(out)

    def catalogue() -> str:
        skills = sorted(registry.list_skills(), key=lambda s: s.name)
        if not skills:
            return "_No skills yet._"
        rows = "\n".join(
            f"- **{s.name}** `v{s.manifest.version}` — {s.manifest.description.splitlines()[0][:90]}"
            for s in skills
        )
        return f"<span class='step'>In the registry ({len(skills)})</span>\n\n{rows}"

    with gr.Blocks(css=_THEME_CSS, theme=gr.themes.Soft(), title="Skill Registry") as demo:
        gr.HTML(
            "<div id='hero'><span class='badge'>MCP Skill Registry</span>"
            "<h1>Publish a skill</h1>"
            "<p>Upload a folder, we check the format, then install &amp; publish it.</p></div>"
        )
        with gr.Column(elem_classes="card"):
            gr.Markdown(_FORMAT_HELP)
        with gr.Column(elem_classes="card"):
            gr.Markdown("<span class='step'>Step 1 — choose your skill</span>")
            file_in = gr.File(label="Skill .zip", file_types=[".zip"], type="binary")
            overwrite = gr.Checkbox(label="Overwrite if a skill with the same name exists")
            gr.Markdown("<span class='step'>Step 2 — validate, then publish</span>")
            with gr.Row():
                validate_btn = gr.Button("Validate format", variant="secondary")
                publish_btn = gr.Button("Upload & Publish", variant="primary")
            output = gr.Markdown()
        with gr.Column(elem_classes="card"):
            cat = gr.Markdown(catalogue())

        validate_btn.click(validate, inputs=file_in, outputs=output)
        publish_btn.click(publish, inputs=[file_in, overwrite], outputs=output).then(
            catalogue, outputs=cat
        )

    return demo
