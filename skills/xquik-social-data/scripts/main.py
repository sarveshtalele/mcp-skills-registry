"""Entrypoint for the ``xquik-social-data`` skill."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

_DEFAULT_BASE_URL = "https://xquik.com"
_HEADER_NAMES = ["X-API-Key"]
_TWEET_SEARCH_PATH = "/api/v1/x/tweets/search"
_TRENDS_PATH = "/api/v1/x/trends"


def _clamp_int(value: object, *, default: int, minimum: int, maximum: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int | float):
        candidate = int(value)
    elif isinstance(value, str) and value.strip():
        try:
            candidate = int(value)
        except ValueError:
            return default
    else:
        return default
    return max(minimum, min(maximum, candidate))


def _clean_base_url(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return _DEFAULT_BASE_URL
    return value.strip().rstrip("/")


def _clean_string(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _request_plan(
    *,
    base_url: str,
    path: str,
    query: dict[str, object],
) -> dict[str, object]:
    clean_query = {
        key: value
        for key, value in query.items()
        if value not in ("", None)
    }
    suffix = f"?{urlencode(clean_query)}" if clean_query else ""
    return {
        "method": "GET",
        "base_url": base_url,
        "path": path,
        "url": f"{base_url}{path}{suffix}",
        "query": clean_query,
        "required_headers": _HEADER_NAMES,
    }


def _first_list(data: dict[str, Any], names: tuple[str, ...]) -> list[Any]:
    for name in names:
        value = data.get(name)
        if isinstance(value, list):
            return value
    nested = data.get("data")
    if isinstance(nested, dict):
        return _first_list(nested, names)
    return []


def _first_text(data: dict[str, Any], names: tuple[str, ...]) -> str:
    for name in names:
        value = data.get(name)
        if isinstance(value, str) and value:
            return value
    return ""


def _first_number(data: dict[str, Any], names: tuple[str, ...]) -> int | float | None:
    for name in names:
        value = data.get(name)
        if isinstance(value, bool):
            continue
        if isinstance(value, int | float):
            return value
    return None


def _author_field(tweet: dict[str, Any], field: str) -> str:
    author = tweet.get("author")
    if isinstance(author, dict):
        value = author.get(field)
        if isinstance(value, str):
            return value
    user = tweet.get("user")
    if isinstance(user, dict):
        value = user.get(field)
        if isinstance(value, str):
            return value
    return _first_text(tweet, (f"author_{field}", field))


def _metrics(tweet: dict[str, Any]) -> dict[str, int | float]:
    candidates = {
        "likes": ("like_count", "likes", "favorite_count", "favoriteCount"),
        "replies": ("reply_count", "replies", "replyCount"),
        "reposts": ("retweet_count", "retweets", "retweetCount"),
        "quotes": ("quote_count", "quotes", "quoteCount"),
        "views": ("view_count", "views", "viewCount"),
    }
    metrics: dict[str, int | float] = {}
    nested = tweet.get("metrics")
    if isinstance(nested, dict):
        for key, value in nested.items():
            if isinstance(value, bool):
                continue
            if isinstance(value, int | float):
                metrics[str(key)] = value
    for output_name, names in candidates.items():
        value = _first_number(tweet, names)
        if value is not None:
            metrics[output_name] = value
    return metrics


def _media(tweet: dict[str, Any]) -> list[Any]:
    value = tweet.get("media")
    if isinstance(value, list):
        return value
    value = tweet.get("attachments")
    if isinstance(value, list):
        return value
    return []


def _normalize_tweet(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    tweet_id = _first_text(value, ("id", "tweet_id", "tweetId", "rest_id"))
    text = _first_text(value, ("text", "full_text", "fullText"))
    if not tweet_id and not text:
        return None
    return {
        "id": tweet_id,
        "text": text,
        "author_username": _author_field(value, "username"),
        "author_name": _author_field(value, "name"),
        "created_at": _first_text(value, ("created_at", "createdAt")),
        "url": _first_text(value, ("url", "tweet_url", "tweetUrl")),
        "metrics": _metrics(value),
        "media": _media(value),
    }


def _normalize_trend(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    name = _first_text(value, ("name", "trend", "query"))
    if not name:
        return None
    return {
        "name": name,
        "query": _first_text(value, ("query", "search_query", "searchQuery")),
        "url": _first_text(value, ("url",)),
        "volume": _first_number(value, ("tweet_volume", "tweetVolume", "volume")),
    }


def _next_cursor(data: dict[str, Any]) -> str:
    cursor = _first_text(data, ("next_cursor", "nextCursor", "cursor"))
    if cursor:
        return cursor
    nested = data.get("data")
    if isinstance(nested, dict):
        return _first_text(nested, ("next_cursor", "nextCursor", "cursor"))
    return ""


def _normalize_records(operation: str, response: object) -> tuple[list[dict[str, object]], str]:
    if not isinstance(response, dict):
        return [], ""
    if operation == "trends":
        values = _first_list(response, ("trends", "items"))
        records = [
            record for record in (_normalize_trend(value) for value in values) if record is not None
        ]
        return records, ""
    if operation == "tweet_lookup":
        tweet = response.get("tweet")
        nested = response.get("data")
        if not isinstance(tweet, dict) and isinstance(nested, dict):
            tweet = nested.get("tweet")
        record = _normalize_tweet(tweet)
        if record is not None:
            return [record], ""
    values = _first_list(response, ("tweets", "items", "results", "data"))
    if not values:
        tweet = response.get("tweet")
        if isinstance(tweet, dict):
            values = [tweet]
        elif operation == "tweet_lookup":
            data = response.get("data")
            if isinstance(data, dict):
                values = [data]
            else:
                values = [response]
    records = [
        record for record in (_normalize_tweet(value) for value in values) if record is not None
    ]
    return records, _next_cursor(response)


def _build_tweet_search(inputs: dict[str, Any], base_url: str) -> dict[str, object]:
    query = _clean_string(inputs.get("query"))
    if not query:
        raise ValueError("tweet_search requires query")
    count = _clamp_int(inputs.get("count"), default=30, minimum=1, maximum=100)
    request = _request_plan(
        base_url=base_url,
        path=_TWEET_SEARCH_PATH,
        query={
            "q": query,
            "limit": count,
            "cursor": _clean_string(inputs.get("cursor")),
        },
    )
    records, next_cursor = _normalize_records("tweet_search", inputs.get("response"))
    return {
        "request": request,
        "records": records,
        "next_cursor": next_cursor,
        "summary": {"operation": "tweet_search", "record_count": len(records)},
    }


def _build_tweet_lookup(inputs: dict[str, Any], base_url: str) -> dict[str, object]:
    tweet_id = _clean_string(inputs.get("tweet_id"))
    if not tweet_id:
        raise ValueError("tweet_lookup requires tweet_id")
    request = _request_plan(
        base_url=base_url,
        path=f"/api/v1/x/tweets/{tweet_id}",
        query={},
    )
    records, _ = _normalize_records("tweet_lookup", inputs.get("response"))
    return {
        "request": request,
        "records": records,
        "next_cursor": "",
        "summary": {"operation": "tweet_lookup", "record_count": len(records)},
    }


def _build_trends(inputs: dict[str, Any], base_url: str) -> dict[str, object]:
    count = _clamp_int(inputs.get("count"), default=30, minimum=1, maximum=50)
    woeid = _clamp_int(inputs.get("woeid"), default=1, minimum=1, maximum=2_147_483_647)
    request = _request_plan(
        base_url=base_url,
        path=_TRENDS_PATH,
        query={"woeid": woeid, "count": count},
    )
    records, _ = _normalize_records("trends", inputs.get("response"))
    return {
        "request": request,
        "records": records,
        "next_cursor": "",
        "summary": {"operation": "trends", "record_count": len(records)},
    }


def _normalize_only(inputs: dict[str, Any]) -> dict[str, object]:
    records, next_cursor = _normalize_records("normalize_tweets", inputs.get("response"))
    return {
        "request": {},
        "records": records,
        "next_cursor": next_cursor,
        "summary": {"operation": "normalize_tweets", "record_count": len(records)},
    }


def run(inputs: dict) -> dict:
    """Prepare a request plan or normalize supplied Xquik response JSON."""
    operation = _clean_string(inputs.get("operation"))
    base_url = _clean_base_url(inputs.get("base_url"))
    if operation == "tweet_search":
        return _build_tweet_search(inputs, base_url)
    if operation == "tweet_lookup":
        return _build_tweet_lookup(inputs, base_url)
    if operation == "trends":
        return _build_trends(inputs, base_url)
    if operation == "normalize_tweets":
        return _normalize_only(inputs)
    raise ValueError(f"unsupported operation: {operation}")
