"""Entrypoint for the ``text-statistics`` skill.

Contract: expose a ``run(inputs: dict) -> dict`` callable. Inputs are validated by
the registry against ``SKILL.md`` before this function is called.
"""

from __future__ import annotations

import re

_SENTENCE_RE = re.compile(r"[.!?]+")
_WORD_RE = re.compile(r"[A-Za-z0-9']+")
_VOWEL_GROUP_RE = re.compile(r"[aeiouy]+")


def _count_syllables(word: str) -> int:
    """Approximate the syllable count of a single word."""
    word = word.lower()
    groups = _VOWEL_GROUP_RE.findall(word)
    count = len(groups)
    if word.endswith("e") and count > 1:
        count -= 1  # silent trailing 'e'
    return max(count, 1)


def run(inputs: dict) -> dict:
    """Compute text statistics for ``inputs['text']``."""
    text: str = inputs["text"]

    words = _WORD_RE.findall(text)
    sentences = [s for s in _SENTENCE_RE.split(text) if s.strip()]
    word_count = len(words)
    sentence_count = max(len(sentences), 1)
    character_count = len(text)
    syllable_count = sum(_count_syllables(w) for w in words)

    avg_word_length = round(sum(len(w) for w in words) / word_count, 2) if word_count else 0.0

    if word_count:
        words_per_sentence = word_count / sentence_count
        syllables_per_word = syllable_count / word_count
        flesch = 206.835 - 1.015 * words_per_sentence - 84.6 * syllables_per_word
    else:
        flesch = 0.0

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "character_count": character_count,
        "avg_word_length": avg_word_length,
        "flesch_reading_ease": round(flesch, 2),
    }
