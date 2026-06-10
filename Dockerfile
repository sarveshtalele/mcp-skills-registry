# Hugging Face Spaces (SDK: docker) image for the MCP Skill Registry.
FROM python:3.11-slim

# Persist runtime data and uploaded skills on the Space's /data mount.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    SKILLREG_PORT=7860 \
    SKILLREG_DB_PATH=/data/registry.db \
    SKILLREG_SKILLS_DIR=/data/skills

WORKDIR /app

# git is required by skills that clone repositories (e.g. reverse-engineering)
# and by git-diff-based analysis (change-impact-analysis).
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Install the package first (better layer caching).
COPY pyproject.toml requirements.txt ./
COPY src/ ./src/
RUN pip install --upgrade pip && pip install .

# Application code: skills catalogue + entrypoint + helper scripts.
COPY app.py ./
COPY skills/ ./skills/
COPY scripts/ ./scripts/

# HF Spaces mounts persistent storage at /data; create it for local runs too.
RUN mkdir -p /data/skills && chmod +x scripts/hf_entrypoint.sh

EXPOSE 7860

# Entrypoint seeds /data/skills from the baked-in catalogue, then serves.
CMD ["scripts/hf_entrypoint.sh"]
