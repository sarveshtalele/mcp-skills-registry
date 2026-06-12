---
name: xquik-social-data
version: 1.0.0
description: >
  Prepare and normalize Xquik X data for MCP clients. Build request plans for
  tweet search, tweet lookup, and trends, or normalize supplied Xquik JSON into
  compact records. Trigger when the user asks for Xquik, X data, Twitter data,
  tweet search, trends, or social data ingest.
author: Xquik-dev
license: MIT
category: social-data
tags: [xquik, social-data, twitter, x, mcp, normalization]
execution:
  type: python-script
  entrypoint: scripts/main.py:run
  timeout_seconds: 15
inputs:
  - name: operation
    type: string
    required: true
    description: Operation to prepare or normalize.
    enum: [tweet_search, tweet_lookup, trends, normalize_tweets]
    examples: [tweet_search]
  - name: query
    type: string
    required: false
    default: ""
    description: Search query for tweet_search.
    examples: ["from:xquik_dev"]
  - name: tweet_id
    type: string
    required: false
    default: ""
    description: Tweet ID for tweet_lookup.
  - name: count
    type: integer
    required: false
    default: 30
    description: Requested item count. Tweet search is clamped to 100 and trends to 50.
  - name: cursor
    type: string
    required: false
    default: ""
    description: Optional pagination cursor for tweet_search.
  - name: woeid
    type: integer
    required: false
    default: 1
    description: Where On Earth ID for trends.
  - name: base_url
    type: string
    required: false
    default: "https://xquik.com"
    description: Base URL used when building request metadata.
  - name: response
    type: object
    required: false
    default: {}
    description: Optional Xquik JSON response to normalize.
outputs:
  - name: request
    type: object
    description: HTTP request plan with method, URL, path, query, and required headers.
  - name: records
    type: array
    items: object
    description: Normalized tweet or trend records.
  - name: summary
    type: object
    description: Operation summary and normalization counts.
  - name: next_cursor
    type: string
    description: Pagination cursor when present in the supplied response.
status: active
---

# Xquik Social Data Skill

Build Xquik API request plans and normalize supplied Xquik response JSON into
compact records for MCP tools and downstream analysis.

## Operations

- `tweet_search` prepares `GET /api/v1/x/tweets/search`.
- `tweet_lookup` prepares `GET /api/v1/x/tweets/{id}`.
- `trends` prepares `GET /api/v1/x/trends`.
- `normalize_tweets` converts supplied tweet response JSON into compact records.

The skill does not make network calls. Add the API key only in the client that
executes the returned request plan.
