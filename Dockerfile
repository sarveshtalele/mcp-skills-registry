# syntax=docker/dockerfile:1
# ---- Stage 1: build the Next.js dashboard to a static export ----
FROM node:20-slim AS frontend
WORKDIR /fe
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build   # produces /fe/out (output: "export")

# ---- Stage 2: Python runtime serving API + MCP + static UI ----
FROM python:3.11-slim

# git is required by skills that clone repositories (reverse-engineering) and by
# git-diff-based analysis (change-impact-analysis).
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    SKILLREG_PORT=7860 \
    SKILLREG_DB_PATH=/data/registry.db \
    SKILLREG_SKILLS_DIR=/data/skills \
    SKILLREG_AGENTS_DIR=/data/agents \
    SKILLREG_FRONTEND_DIR=/app/frontend/out

WORKDIR /app

# Install the package (better layer caching).
COPY pyproject.toml requirements.txt ./
COPY src/ ./src/
RUN pip install --upgrade pip && pip install .

# Application assets.
COPY app.py ./
COPY skills/ ./skills/
COPY agents/ ./agents/
COPY scripts/ ./scripts/
COPY --from=frontend /fe/out ./frontend/out

RUN mkdir -p /data/skills /data/agents && chmod +x scripts/hf_entrypoint.sh

EXPOSE 7860

# Entrypoint seeds /data from the baked-in catalogue, then serves.
CMD ["scripts/hf_entrypoint.sh"]
