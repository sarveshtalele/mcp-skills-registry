# Xquik Social Data

Prepare Xquik API request plans and normalize supplied response JSON into compact
records for MCP clients.

## Example

```json
{
  "operation": "tweet_search",
  "query": "from:xquik_dev",
  "count": 10
}
```

The skill returns a request plan for `GET /api/v1/x/tweets/search`. It also
normalizes supplied tweet responses into stable fields such as `id`, `text`,
`author_username`, `created_at`, `url`, and `metrics`.
