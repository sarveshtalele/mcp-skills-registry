"""Execution tests for the Xquik social data skill."""

from __future__ import annotations

from skill_registry.models import ExecutionStatus


async def test_execute_xquik_tweet_search_plan(registry):
    result = await registry.execute(
        "xquik-social-data",
        {
            "operation": "tweet_search",
            "query": "from:xquik_dev",
            "count": 2,
        },
    )

    assert result.status is ExecutionStatus.SUCCESS
    assert result.output is not None
    request = result.output["request"]
    assert request["method"] == "GET"
    assert request["path"] == "/api/v1/x/tweets/search"
    assert request["query"] == {"q": "from:xquik_dev", "limit": 2}
    assert request["required_headers"] == ["X-API-Key"]
    assert result.output["summary"] == {"operation": "tweet_search", "record_count": 0}


async def test_execute_xquik_tweet_lookup_normalizes_tweet_response(registry):
    result = await registry.execute(
        "xquik-social-data",
        {
            "operation": "tweet_lookup",
            "tweet_id": "123",
            "response": {
                "tweet": {
                    "id": "123",
                    "text": "lookup result",
                    "author": {"username": "alice", "name": "Alice"},
                    "created_at": "2026-06-12T00:00:00Z",
                    "reply_count": 4,
                }
            },
        },
    )

    assert result.status is ExecutionStatus.SUCCESS
    assert result.output is not None
    assert result.output["request"]["path"] == "/api/v1/x/tweets/123"
    assert result.output["summary"] == {"operation": "tweet_lookup", "record_count": 1}
    assert result.output["records"] == [
        {
            "id": "123",
            "text": "lookup result",
            "author_username": "alice",
            "author_name": "Alice",
            "created_at": "2026-06-12T00:00:00Z",
            "url": "",
            "metrics": {"replies": 4},
            "media": [],
        }
    ]


async def test_execute_xquik_normalizes_response(registry):
    result = await registry.execute(
        "xquik-social-data",
        {
            "operation": "normalize_tweets",
            "response": {
                "tweets": [
                    {
                        "id": "123",
                        "text": "hello",
                        "author": {"username": "alice", "name": "Alice"},
                        "created_at": "2026-06-12T00:00:00Z",
                        "like_count": 3,
                    }
                ],
                "next_cursor": "cursor-2",
            },
        },
    )

    assert result.status is ExecutionStatus.SUCCESS
    assert result.output is not None
    assert result.output["next_cursor"] == "cursor-2"
    assert result.output["summary"] == {"operation": "normalize_tweets", "record_count": 1}
    assert result.output["records"] == [
        {
            "id": "123",
            "text": "hello",
            "author_username": "alice",
            "author_name": "Alice",
            "created_at": "2026-06-12T00:00:00Z",
            "url": "",
            "metrics": {"likes": 3},
            "media": [],
        }
    ]


async def test_execute_xquik_trends_plan_clamps_count(registry):
    result = await registry.execute(
        "xquik-social-data",
        {
            "operation": "trends",
            "count": 200,
            "woeid": 1,
        },
    )

    assert result.status is ExecutionStatus.SUCCESS
    assert result.output is not None
    request = result.output["request"]
    assert request["path"] == "/api/v1/x/trends"
    assert request["query"] == {"woeid": 1, "count": 50}
