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

    # --- API exposure / hardening ---
    # Interactive API docs (/docs, /redoc, /openapi.json) are OFF by default so the
    # schema isn't public. Enable explicitly in trusted/dev environments.
    enable_docs: bool = False
    # CORS allowed origins, comma-separated ("*" = any). Tighten in production.
    cors_allow_origins: str = "*"
    # Admin token gating mutating endpoints (upload/delete/reload). When set, those
    # endpoints require header `X-Admin-Token: <token>`. Empty = open (logs a warning).
    admin_token: str = ""
    # Max bytes of JSON inputs accepted by an execute request.
    max_input_bytes: int = 256_000
    # Env var names a skill subprocess is allowed to see (e.g. integration creds).
    # The server's own secrets are NEVER exposed regardless of this list.
    skill_env_allowlist: str = (
        "JIRA_BASE_URL,JIRA_EMAIL,JIRA_API_TOKEN,"
        "SERVICENOW_INSTANCE,SERVICENOW_USER,SERVICENOW_PASSWORD"
    )

    # --- Paths ---
    skills_dir: Path = Path("skills")
    agents_dir: Path = Path("agents")
    db_path: Path = Path("data/registry.db")

    # --- Execution sandbox ---
    default_timeout_seconds: int = 30
    max_timeout_seconds: int = 120
    max_output_bytes: int = 1_000_000

    # --- Skill uploads ---
    enable_uploads: bool = True
    max_upload_bytes: int = 5_000_000
    max_uncompressed_bytes: int = 25_000_000

    # --- GitHub auto-publish (optional) ---
    # When a GitHub token is present, uploaded skills are also committed to the
    # repository's skills/ folder, which redeploys the Space.
    github_token: str = ""
    github_repo: str = "sarveshtalele/mcp-skills-registry"
    github_branch: str = "main"

    # --- UI ---
    enable_ui: bool = True
    frontend_dir: Path = Path("frontend/out")

    @property
    def github_publish_enabled(self) -> bool:
        """True when GitHub auto-publish is configured."""
        return bool(self.github_token and self.github_repo)

    @property
    def cors_origin_list(self) -> list[str]:
        """Parsed CORS origins."""
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()] or ["*"]

    @property
    def skill_env_allow(self) -> set[str]:
        """Set of env var names a skill subprocess may receive."""
        return {n.strip() for n in self.skill_env_allowlist.split(",") if n.strip()}

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
    def resolved_agents_dir(self) -> Path:
        """Absolute path to the agents directory."""
        return self.agents_dir.expanduser().resolve()

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
