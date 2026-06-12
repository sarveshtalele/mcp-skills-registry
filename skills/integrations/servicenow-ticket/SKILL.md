---
name: servicenow-ticket
version: 1.0.0
description: >
  Create a ServiceNow incident via the Table API. Requires SERVICENOW_INSTANCE,
  SERVICENOW_USER, and SERVICENOW_PASSWORD environment variables on the server.
  Trigger on: create a ServiceNow incident, raise an ITSM ticket, log an incident.
author: sarveshtalele
license: MIT
category: integrations
tags: [integration, servicenow, itsm, ticketing]
execution:
  type: python-script
  entrypoint: scripts/main.py:run
  timeout_seconds: 30
requires_approval: true
inputs:
  - name: short_description
    type: string
    required: true
    description: Incident short description (title).
  - name: description
    type: string
    required: false
    description: Detailed incident description.
  - name: urgency
    type: string
    required: false
    default: "3"
    description: Urgency 1 (high) to 3 (low).
outputs:
  - name: number
    type: string
    description: The created incident number (e.g. INC0012345).
  - name: sys_id
    type: string
    description: The ServiceNow sys_id of the record.
status: active
---

# servicenow-ticket

Creates a ServiceNow incident. Credentials come from the environment; returns the
incident number and sys_id, or a clear error if credentials are missing.
