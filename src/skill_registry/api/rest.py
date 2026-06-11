"""Human/programmatic REST API for browsing and running skills."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from skill_registry.api.deps import get_registry
from skill_registry.errors import ManifestError, SkillNotFoundError
from skill_registry.models import (
    AgentManifest,
    AgentSummary,
    ExecutionRequest,
    ExecutionResult,
    SkillManifest,
    SkillSummary,
)
from skill_registry.services import InstallError, SkillRegistry

router = APIRouter(prefix="/api/v1", tags=["skills"])


@router.get("/skills", response_model=list[SkillSummary])
async def list_skills(
    q: str | None = Query(None, description="Free-text search query"),
    category: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    registry: SkillRegistry = Depends(get_registry),
) -> list[SkillSummary]:
    """Search or list skills."""
    return registry.search(q, category=category, limit=limit, offset=offset)


@router.get("/skills/{name}", response_model=SkillManifest)
async def get_skill(name: str, registry: SkillRegistry = Depends(get_registry)) -> SkillManifest:
    """Return a skill's full manifest."""
    try:
        return registry.get_manifest(name)
    except SkillNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/skills/{name}/execute", response_model=ExecutionResult)
async def execute_skill(
    name: str,
    request: ExecutionRequest,
    registry: SkillRegistry = Depends(get_registry),
) -> ExecutionResult:
    """Execute a skill with the supplied inputs."""
    try:
        return await registry.execute(
            name, request.inputs, version=request.version, user_id=request.user_id
        )
    except SkillNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/skills/upload", response_model=SkillManifest, status_code=201)
async def upload_skill(
    file: UploadFile = File(..., description="A .zip archive containing SKILL.md"),
    overwrite: bool = Query(False, description="Replace an existing skill of the same name"),
    registry: SkillRegistry = Depends(get_registry),
) -> SkillManifest:
    """Upload and install a skill packaged as a ZIP archive.

    The archive must contain a ``SKILL.md`` (at the root or one folder deep). The
    skill name is taken from the manifest; files install into ``skills/<name>/``.
    """
    data = await file.read()
    try:
        return registry.install_zip(data, overwrite=overwrite)
    except InstallError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ManifestError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/agents", response_model=list[AgentSummary])
async def list_agents(registry: SkillRegistry = Depends(get_registry)) -> list[AgentSummary]:
    """List registered agents."""
    return [AgentSummary.from_manifest(a.manifest) for a in registry.list_agents()]


@router.get("/agents/{name}", response_model=AgentManifest)
async def get_agent(name: str, registry: SkillRegistry = Depends(get_registry)) -> AgentManifest:
    """Return an agent's full manifest."""
    try:
        return registry.get_agent(name).manifest
    except SkillNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/agents/upload", response_model=AgentManifest, status_code=201)
async def upload_agent(
    file: UploadFile = File(..., description="A .zip archive containing AGENT.md"),
    overwrite: bool = Query(False),
    registry: SkillRegistry = Depends(get_registry),
) -> AgentManifest:
    """Upload and install an agent packaged as a ZIP (must contain AGENT.md)."""
    data = await file.read()
    try:
        return registry.install_and_publish_agent(data, overwrite=overwrite)["manifest"]
    except InstallError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ManifestError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/skills/validate", response_model=SkillManifest)
async def validate_skill(
    file: UploadFile = File(...),
    registry: SkillRegistry = Depends(get_registry),
) -> SkillManifest:
    """Validate a skill ZIP without installing it."""
    try:
        return registry.validate_upload(await file.read())
    except (InstallError, ManifestError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/agents/validate", response_model=AgentManifest)
async def validate_agent(
    file: UploadFile = File(...),
    registry: SkillRegistry = Depends(get_registry),
) -> AgentManifest:
    """Validate an agent ZIP without installing it."""
    try:
        return registry.validate_agent_upload(await file.read())
    except (InstallError, ManifestError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/admin/reload")
async def reload_catalogue(registry: SkillRegistry = Depends(get_registry)) -> dict:
    """Re-scan the skills directory (useful after adding a skill)."""
    count = registry.reload()
    return {"status": "ok", "skills_loaded": count}
