"""Skill discovery: keyword scoring by default, optional semantic ranking.

Semantic search (sentence-transformers) is opt-in and lazily initialised, so the
core server has no heavy ML dependency unless explicitly enabled.
"""

from __future__ import annotations

from collections.abc import Iterable

from skill_registry.config import Settings
from skill_registry.logging_config import get_logger
from skill_registry.models import SkillStatus, SkillSummary
from skill_registry.services.loader import LoadedSkill

_logger = get_logger(__name__)


class SearchService:
    """Ranks skills against a free-text query."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model = None  # lazily loaded sentence-transformers model

    def search(
        self,
        query: str | None,
        skills: Iterable[LoadedSkill],
        *,
        category: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[SkillSummary]:
        """Return ranked summaries matching the query and filters."""
        candidates = [
            s
            for s in skills
            if s.manifest.status is not SkillStatus.ARCHIVED
            and (category is None or s.manifest.category == category)
        ]

        if not query:
            ordered = sorted(candidates, key=lambda s: s.name)
            summaries = [SkillSummary.from_manifest(s.manifest) for s in ordered]
            return summaries[offset : offset + limit]

        scored = self._score(query, candidates)
        scored.sort(key=lambda pair: pair[1], reverse=True)
        ranked = [
            SkillSummary.from_manifest(skill.manifest, relevance=round(score, 4))
            for skill, score in scored
            if score > 0
        ]
        return ranked[offset : offset + limit]

    def _score(self, query: str, candidates: list[LoadedSkill]) -> list[tuple[LoadedSkill, float]]:
        if self._settings.enable_semantic_search:
            model = self._get_model()
            if model is not None:
                return self._semantic_score(model, query, candidates)
        return [(s, self._keyword_score(query, s)) for s in candidates]

    @staticmethod
    def _keyword_score(query: str, skill: LoadedSkill) -> float:
        terms = {t for t in query.lower().split() if t}
        if not terms:
            return 0.0
        m = skill.manifest
        haystack = " ".join([m.name, m.description, m.category, " ".join(m.tags)]).lower()
        hits = sum(1 for term in terms if term in haystack)
        score = hits / len(terms)
        # Light boost when a term matches the name directly.
        if any(term in m.name.lower() for term in terms):
            score += 0.25
        return min(score, 1.0)

    def _semantic_score(
        self, model, query: str, candidates: list[LoadedSkill]
    ) -> list[tuple[LoadedSkill, float]]:
        from numpy import dot  # local import keeps numpy optional
        from numpy.linalg import norm

        query_vec = model.encode(query)
        scored: list[tuple[LoadedSkill, float]] = []
        for skill in candidates:
            text = f"{skill.manifest.name}. {skill.manifest.description}"
            vec = model.encode(text)
            denom = float(norm(query_vec) * norm(vec)) or 1.0
            scored.append((skill, float(dot(query_vec, vec) / denom)))
        return scored

    def _get_model(self):
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._settings.embedding_model)
            _logger.info("Semantic search model '%s' loaded", self._settings.embedding_model)
        except ImportError:
            _logger.warning(
                "Semantic search enabled but sentence-transformers is not installed; "
                "falling back to keyword search. Install the 'search' extra."
            )
            self._model = None
        return self._model
