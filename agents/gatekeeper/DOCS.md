        # gatekeeper — file reference

        | File | What it does |
        |------|--------------|
        | `AGENT.md` | manifest + instructions |
| `system-prompt.md` | role/system prompt |
| `workflow.yaml` | ordered steps; `uses` references a skill |
| `skills.yaml` | skills this agent orchestrates |
| `tools.yaml` | external tools/MCPs the agent may use |
| `governance.yaml` | gate policy |

        The registry reads **AGENT.md** (its frontmatter declares `skills` and
        `workflow`). The other files are the production, machine-readable split of
        that definition for external orchestration tooling.
