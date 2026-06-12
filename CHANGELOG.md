# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Community health files: Code of Conduct, Security Policy, issue/PR templates,
  CODEOWNERS, Dependabot, `.editorconfig`, `CITATION.cff`.
- Architecture diagram in the README.

## [0.2.0] - 2026-06-12

### Added
- **Skills catalogue** — 14 skills across groups: core (`text-statistics`,
  `change-impact-analysis`, `legacy-discovery`), SpecKit SDD (`speckit-*`), the
  Governed Engineering Factory (`topology-planning`, `task-decomposition`,
  `ui-modernization`, `test-generation`, `spec-governance`), and integrations
  (`jira-ticket`, `servicenow-ticket`).
- **Agents** — `arch-analyst`, `migration-eng`, `gatekeeper` with multi-file
  definitions (AGENT.md + workflow/skills/tools YAML).
- **MCP transport** — Streamable HTTP (JSON-RPC 2.0) with session management.
- **REST API** — browse/search, execute, upload, validate, delete; agents API.
- **Next.js dashboard** (Apple-inspired) served by the FastAPI app; upload skills,
  spec-kit skills, and agents with validate + publish.
- **GitHub auto-publish** — uploads can commit to `skills/` or `agents/`.
- **Sandboxed execution** — isolated subprocess + timeout + output cap.

### Changed
- Merged `reverse-engineering` into `legacy-discovery` (one skill, two modes:
  remote URL clone or local path scan); remote mode now renders a code-free,
  chief-architect report.
- Lenient uploads: manifests are coerced rather than rejected; the response
  reports the installed file tree and advisories.

## [0.1.0] - 2026-06-10

### Added
- Initial modular FastAPI MCP server with on-disk skill discovery, SQLite-backed
  execution history and audit log, and Hugging Face Spaces deployment.
