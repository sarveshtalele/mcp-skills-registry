"""Hugging Face Spaces / uvicorn entrypoint.

Exposes the ASGI ``app`` and a ``__main__`` runner. The real application lives in
the ``skill_registry`` package under ``src/`` — this thin shim keeps the platform
entrypoint stable while the implementation stays modular.
"""

from skill_registry.main import app, run_cli  # noqa: F401  (re-exported for ASGI servers)

if __name__ == "__main__":
    run_cli()
