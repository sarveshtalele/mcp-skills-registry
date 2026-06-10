"""Application factory and entrypoints.

``create_app`` builds a configured FastAPI instance. ``app`` is the module-level
ASGI app that Hugging Face Spaces / uvicorn import. ``run_cli`` runs a dev server.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from skill_registry.api import health, mcp, rest
from skill_registry.config import Settings, get_settings
from skill_registry.container import build_container
from skill_registry.logging_config import configure_logging, get_logger

_logger = get_logger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        container = build_container(settings)
        app.state.settings = container.settings
        app.state.registry = container.registry
        app.state.mcp_handler = container.mcp_handler
        app.state.sessions = container.sessions
        _logger.info(
            "%s v%s ready with %d skill(s)",
            settings.title,
            settings.version,
            len(container.registry.list_skills()),
        )
        yield

    app = FastAPI(
        title=settings.title,
        version=settings.version,
        description="Discover and execute community MCP skills.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(mcp.router)
    app.include_router(rest.router)
    return app


# Module-level ASGI app for `uvicorn skill_registry.main:app` and HF Spaces.
app = create_app()


def run_cli() -> None:
    """Run a development server (entrypoint: ``skill-registry``)."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "skill_registry.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run_cli()
