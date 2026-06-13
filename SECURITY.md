# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.2.x   | ✅        |
| < 0.2   | ❌        |

## Reporting a Vulnerability

**Do not open a public issue for security vulnerabilities.**

Please report them privately via GitHub Security Advisories
([Report a vulnerability](https://github.com/sarveshtalele/mcp-skills-registry/security/advisories/new))
or by email to **talelesarvesh@gmail.com**.

Include:

- A description of the vulnerability and its impact
- Steps to reproduce (proof of concept if possible)
- Affected version/commit

You will receive an acknowledgement within **72 hours** and a remediation plan
once the report is triaged.

## Security Model & Hardening

- **Sandboxed execution** — skills run in isolated subprocesses with a hard
  timeout and an output-size cap; a misbehaving skill cannot hang or crash the server.
- **Secret isolation** — skill subprocesses receive a **scrubbed environment**:
  only base-safe vars + an explicit allow-list (`SKILLREG_SKILL_ENV_ALLOWLIST`,
  e.g. integration creds). The server's own secrets (`SKILLREG_GITHUB_TOKEN`, HF
  tokens, admin token) are **never** exposed to skill code.
- **Upload safety** — uploaded archives are validated and guarded against
  path traversal (zip-slip) and decompression bombs; uploads can be disabled with
  `SKILLREG_ENABLE_UPLOADS=false`.
- **Authenticated mutations** — set `SKILLREG_ADMIN_TOKEN` to require an
  `X-Admin-Token` header on upload / delete / reload. Without it those endpoints
  are open (a startup warning is logged) — **always set it in production**.
- **Hidden API schema** — `/docs`, `/redoc`, `/openapi.json` are **off by default**
  (`SKILLREG_ENABLE_DOCS=false`).
- **CORS** — configurable via `SKILLREG_CORS_ALLOW_ORIGINS` (tighten from `*`).
- **Input cap** — execute payloads are bounded by `SKILLREG_MAX_INPUT_BYTES`.
- **No secrets in the repo** — `.env` is gitignored; only `.env.example` ships.

## Hardening Recommendations for Operators

- Run behind TLS and a reverse proxy.
- Restrict who can upload skills (front the upload endpoints with auth) in
  multi-tenant deployments.
- Review third-party skills before enabling auto-publish to GitHub.
