# Agents

Agents orchestrate registry skills through a workflow. Each `AGENT.md` declares
the skills it uses and the steps it runs. Clients load an agent to drive a
multi-step process (e.g. legacy modernization) end to end.

| Agent | Purpose | Skills |
|-------|---------|--------|
| `arch-analyst` | Reverse-engineer & define target architecture | legacy-discovery, topology-planning |
| `migration-eng` | Build the modernization solution | task-decomposition, ui-modernization, test-generation |
| `gatekeeper` | Governance & compliance enforcement | spec-governance |
