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
- **Upload safety** — uploaded archives are validated and guarded against
  path traversal (zip-slip) and decompression bombs; uploads can be disabled with
  `SKILLREG_ENABLE_UPLOADS=false`.
- **Secrets** — integration skills read credentials from environment variables
  only; never hard-code secrets. Configure them as Hugging Face Space secrets.
- **No secrets in the repo** — `.env` is gitignored; only `.env.example` ships.

## Hardening Recommendations for Operators

- Run behind TLS and a reverse proxy.
- Restrict who can upload skills (front the upload endpoints with auth) in
  multi-tenant deployments.
- Review third-party skills before enabling auto-publish to GitHub.
