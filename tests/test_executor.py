"""End-to-end execution tests through the registry facade."""

from __future__ import annotations

from skill_registry.models import ExecutionStatus


async def test_execute_text_statistics(registry):
    result = await registry.execute(
        "text-statistics", {"text": "The quick brown fox jumps over the lazy dog."}
    )
    assert result.status is ExecutionStatus.SUCCESS
    assert result.output["word_count"] == 9
    assert result.output["sentence_count"] == 1
    assert result.duration_ms >= 0


async def test_execute_invalid_input(registry):
    result = await registry.execute("text-statistics", {"text": 123})
    assert result.status is ExecutionStatus.INVALID_INPUT


async def test_execute_unknown_skill(registry):
    import pytest

    from skill_registry.errors import SkillNotFoundError

    with pytest.raises(SkillNotFoundError):
        await registry.execute("does-not-exist", {})
