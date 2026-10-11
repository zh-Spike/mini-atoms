import secrets
from collections import Counter
from datetime import UTC, datetime
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request

from app import metrics
from app.agents.pipeline import latest_version
from app.api.projects import _get_project
from app.auth import CurrentUser, DbSession
from app.models import Share, ShareView
from app.serializers import share_out

router = APIRouter(prefix="/api", tags=["share"])

DIRECT = "直接访问"
MOBILE_MARKERS = ("Mobi", "Android", "iPhone", "iPad")


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


def _referrer_host(ref: str, own_host: str) -> str:
    host = (urlsplit(ref).hostname or "").lower()[:255]
    return "" if not host or host == own_host else host


@router.get("/projects/{project_id}/share/stats")
def share_stats(project_id: str, user: CurrentUser, db: DbSession, days: int = 7) -> dict:
    project = _get_project(db, user, project_id)
    if project.share is None:
        raise HTTPException(status_code=404, detail="项目尚未发布")
    days = metrics.window_days(days)
    views = (
        db.query(ShareView)
        .filter(ShareView.slug == project.share.slug, ShareView.created_at >= metrics.since(days))
        .all()
    )
    per_day = Counter(metrics.local_day(v.created_at) for v in views)
    referrers = Counter(v.referrer_host or DIRECT for v in views)
    devices = Counter(v.device for v in views)
    return {
        "days": days,
        "views_total": project.share.views,
        "views_window": len(views),
        "daily": [{"date": d.isoformat(), "views": per_day[d]} for d in metrics.day_keys(days)],
        "referrers": [{"host": h, "views": n} for h, n in referrers.most_common(5)],
        "devices": [{"device": d, "views": n} for d, n in devices.most_common()],
    }


@router.get("/share/{slug}")
def view_shared(slug: str, request: Request, db: DbSession, ref: str = "") -> dict:
    share = db.get(Share, slug)
    if share is None:
        raise HTTPException(status_code=404, detail="分享不存在或已取消发布")
    share.views += 1
    agent = request.headers.get("user-agent", "")
    db.add(
        ShareView(
            slug=slug,
            referrer_host=_referrer_host(ref, request.url.hostname or ""),
            device="mobile" if any(m in agent for m in MOBILE_MARKERS) else "desktop",
        )
    )
    db.commit()
    return {
        "title": share.version.project.title,
        "files": share.version.files,
        "version_number": share.version.number,
        "views": share.views,
        "updated_at": share.updated_at.isoformat(),
    }
