---
name: jira-ticket
version: 1.0.0
description: >
  Create a Jira issue via the Jira Cloud REST API. Requires JIRA_BASE_URL,
  JIRA_EMAIL, and JIRA_API_TOKEN environment variables on the server. Trigger
  on: create a Jira ticket, raise a Jira issue, log a bug in Jira, open a story.
author: sarveshtalele
license: MIT
category: integrations
tags: [integration, jira, ticketing, itsm]
execution:
  type: python-script
  entrypoint: scripts/main.py:run
  timeout_seconds: 30
requires_approval: true
inputs:
  - name: project_key
    type: string
    required: true
    description: Jira project key (e.g. "OPS").
  - name: summary
    type: string
    required: true
    description: Issue summary/title.
  - name: description
    type: string
    required: false
    description: Issue description body.
  - name: issue_type
    type: string
    required: false
    default: Task
    description: Issue type (Task, Bug, Story, ...).
outputs:
  - name: key
    type: string
    description: The created issue key (e.g. OPS-123).
  - name: url
    type: string
    description: Browser URL of the created issue.
status: active
---

# jira-ticket

Creates a Jira issue. Credentials come from the environment; the skill returns
the created issue key and URL, or a clear error if credentials are missing.
