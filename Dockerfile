# Hugging Face Spaces (SDK: docker) image for the MCP Skill Registry.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    SKILLREG_PORT=7860 \
    SKILLREG_DB_PATH=/data/registry.db

WORKDIR /app

# Install the package first (better layer caching).
COPY pyproject.toml requirements.txt ./
COPY src/ ./src/
RUN pip install --upgrade pip && pip install .

# Application code: skills catalogue + entrypoint + helper scripts.
COPY app.py ./
COPY skills/ ./skills/
COPY scripts/ ./scripts/

# HF Spaces mounts persistent storage at /data; create it for local runs too.
RUN mkdir -p /data

EXPOSE 7860

CMD ["uvicorn", "skill_registry.main:app", "--host", "0.0.0.0", "--port", "7860"]
