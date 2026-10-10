import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from app.agents.pipeline import latest_version
from app.api.projects import _get_project
from app.auth import CurrentUser, DbSession
from app.models import Share
from app.serializers import share_out

router = APIRouter(prefix="/api", tags=["share"])


@router.post("/projects/{project_id}/share")
def publish(project_id: str, user: CurrentUser, db: DbSession) -> dict:
    project = _get_project(db, user, project_id)
    latest = latest_version(db, project)
    if latest is None:
        raise HTTPException(status_code=400, detail="还没有可发布的版本")
    share = project.share
    if share is None:
        share = Share(slug=secrets.token_urlsafe(6), project_id=project.id, version_id=latest.id)
        db.add(share)
    else:
        share.version_id = latest.id
        share.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(share)
    return share_out(share)


@router.delete("/projects/{project_id}/share")
def unpublish(project_id: str, user: CurrentUser, db: DbSession) -> dict:
    project = _get_project(db, user, project_id)
    if project.share is not None:
        db.delete(project.share)
        db.commit()
    return {"ok": True}


@router.get("/share/{slug}")
def view_shared(slug: str, db: DbSession) -> dict:
    share = db.get(Share, slug)
    if share is None:
        raise HTTPException(status_code=404, detail="分享不存在或已取消发布")
    share.views += 1
    db.commit()
    return {
        "title": share.version.project.title,
        "files": share.version.files,
        "version_number": share.version.number,
        "views": share.views,
        "updated_at": share.updated_at.isoformat(),
    }
