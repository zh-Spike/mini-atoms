import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agents.llm import LLM, get_llm
from app.agents.pipeline import create_version, latest_version, run_pipeline
from app.auth import CurrentUser, DbSession
from app.config import get_settings
from app.db import SessionLocal
from app.models import Project, User, Version
from app.serializers import message_out, project_summary, version_out

router = APIRouter(prefix="/api", tags=["projects"])

MAX_FILES = 40
MAX_FILE_BYTES = 200_000


class ProjectIn(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)


class MessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class ManualVersionIn(BaseModel):
    files: dict[str, str]
    summary: str = Field(default="手动编辑", max_length=500)


def _get_project(db, user: User, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


def _get_version(db, user: User, version_id: str) -> Version:
    version = db.get(Version, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="版本不存在")
    _get_project(db, user, version.project_id)
    return version


@router.get("/projects")
def list_projects(user: CurrentUser, db: DbSession) -> list[dict]:
    projects = (
        db.query(Project)
        .filter(Project.user_id == user.id)
        .order_by(Project.updated_at.desc())
        .all()
    )
    return [project_summary(p) for p in projects]


@router.post("/projects")
def create_project(body: ProjectIn, user: CurrentUser, db: DbSession) -> dict:
    title = body.prompt.strip().splitlines()[0][:40]
    project = Project(user_id=user.id, title=title)
    db.add(project)
    db.commit()
    return project_summary(project)


@router.get("/projects/{project_id}")
def get_project(project_id: str, user: CurrentUser, db: DbSession) -> dict:
    project = _get_project(db, user, project_id)
    latest = latest_version(db, project)
    return {
        **project_summary(project),
        "messages": [message_out(m) for m in project.messages],
        "versions": [version_out(v, include_files=False) for v in reversed(project.versions)],
        "latest_version": version_out(latest) if latest else None,
    }


@router.delete("/projects/{project_id}")
def delete_project(project_id: str, user: CurrentUser, db: DbSession) -> dict:
    project = _get_project(db, user, project_id)
    db.delete(project)
    db.commit()
    return {"ok": True}


@router.get("/versions/{version_id}")
def get_version(version_id: str, user: CurrentUser, db: DbSession) -> dict:
    return version_out(_get_version(db, user, version_id))


@router.post("/versions/{version_id}/restore")
def restore_version(version_id: str, user: CurrentUser, db: DbSession) -> dict:
    old = _get_version(db, user, version_id)
    project = _get_project(db, user, old.project_id)
    version = create_version(db, project, dict(old.files), "restore", f"回滚到 v{old.number}")
    return version_out(version)


@router.post("/projects/{project_id}/versions")
def save_manual_version(
    project_id: str, body: ManualVersionIn, user: CurrentUser, db: DbSession
) -> dict:
    project = _get_project(db, user, project_id)
    if not body.files or len(body.files) > MAX_FILES:
        raise HTTPException(status_code=400, detail="文件数量不合法")
    if any(len(c.encode()) > MAX_FILE_BYTES for c in body.files.values()):
        raise HTTPException(status_code=400, detail="单个文件过大")
    version = create_version(db, project, body.files, "manual", body.summary)
    return version_out(version)


@router.post("/projects/{project_id}/messages")
def send_message(
    project_id: str,
    body: MessageIn,
    user: CurrentUser,
    db: DbSession,
    llm: Annotated[LLM, Depends(get_llm)],
) -> StreamingResponse:
    project = _get_project(db, user, project_id)
    limit = get_settings().user_generation_limit
    if user.generations_used >= limit:
        raise HTTPException(status_code=429, detail=f"已用完 {limit} 次生成额度")
    user.generations_used += 1
    db.commit()

    async def stream() -> AsyncIterator[bytes]:
        # The request-scoped session may close before streaming ends, so use our own.
        with SessionLocal() as run_db:
            run_project = run_db.get(Project, project.id)
            async for event in run_pipeline(run_db, run_project, body.content.strip(), llm):
                yield (json.dumps(event, ensure_ascii=False) + "\n").encode()

    return StreamingResponse(
        stream(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
