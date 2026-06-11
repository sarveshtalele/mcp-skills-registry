# Target architecture patterns

- **microservices** — independently deployable services, API gateway, async messaging, DB-per-service.
- **modular-monolith** — single deployable, enforced module boundaries, internal APIs.
- **serverless** — functions per request flow, externalised state, managed queues.

Default is **microservices** when an unknown style is requested.
