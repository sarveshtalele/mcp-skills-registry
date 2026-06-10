#!/usr/bin/env bash
# Container entrypoint for the Hugging Face Space.
#
# Seeds the persistent skills directory from the image's baked-in skills, then
# starts the server. `cp -rn` (no-clobber) means:
#   - first boot copies all Git-committed skills into /data/skills
#   - later boots add any NEW Git skills without overwriting uploaded ones
#   - skills uploaded via the API persist across rebuilds
set -euo pipefail

SKILLS_DIR="${SKILLREG_SKILLS_DIR:-/data/skills}"
mkdir -p "${SKILLS_DIR}"

if [ -d /app/skills ]; then
    cp -rn /app/skills/. "${SKILLS_DIR}/" 2>/dev/null || true
fi

exec uvicorn skill_registry.main:app --host 0.0.0.0 --port "${SKILLREG_PORT:-7860}"
