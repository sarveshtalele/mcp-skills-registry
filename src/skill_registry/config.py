"""Application configuration, loaded from environment variables and ``.env``.

All settings carry the ``SKILLREG_`` prefix. Defaults are production-safe and let
the server boot with zero configuration (useful on Hugging Face Spaces).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from skill_registry import __version__


class Settings(BaseSettings):
    """Typed application settings."""

    model_config = SettingsConfigDict(
        env_prefix="SKILLREG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 7860
    log_level: str = "INFO"

    # --- Paths ---
    skills_dir: Path = Path("skills")
    db_path: Path = Path("data/registry.db")

    # --- Execution sandbox ---
    default_timeout_seconds: int = 30
    max_timeout_seconds: int = 120
    max_output_bytes: int = 1_000_000

    # --- Skill uploads ---
    enable_uploads: bool = True
    max_upload_bytes: int = 5_000_000
    max_uncompressed_bytes: int = 25_000_000

    # --- Semantic search (optional) ---
    enable_semantic_search: bool = False
    embedding_model: str = "all-MiniLM-L6-v2"

    # --- Metadata ---
    title: str = "MCP Skill Registry"
    version: str = __version__

    @property
    def resolved_skills_dir(self) -> Path:
        """Absolute path to the skills directory."""
        return self.skills_dir.expanduser().resolve()

    @property
    def resolved_db_path(self) -> Path:
        """Absolute path to the SQLite database file."""
        return self.db_path.expanduser().resolve()

    def clamp_timeout(self, requested: int | None) -> int:
        """Clamp a requested timeout to the allowed range."""
        value = requested or self.default_timeout_seconds
        return max(1, min(value, self.max_timeout_seconds))


@lru_cache
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""
    return Settings()
