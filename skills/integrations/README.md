# Integrations — external system connectors

Skills that call external APIs (ticketing, ITSM, etc.). Each reads credentials
from environment variables (set as Space secrets) and **never** hard-codes them.
These skills mutate external systems, so they set `requires_approval: true`.

| Skill | Creates | Required env vars |
|-------|---------|-------------------|
| `jira-ticket` | a Jira issue | `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` |
| `servicenow-ticket` | a ServiceNow incident | `SERVICENOW_INSTANCE`, `SERVICENOW_USER`, `SERVICENOW_PASSWORD` |
