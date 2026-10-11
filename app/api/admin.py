from collections import Counter

from fastapi import APIRouter, HTTPException
from sqlalchemy import func

from app import metrics
from app.api.usage import project_titles
from app.auth import AdminUser, DbSession
from app.config import get_settings
from app.models import InviteCode, LLMCall, Project, Run, Share, ShareView, User, Version

router = APIRouter(prefix="/api/admin", tags=["admin"])

PAGE_SIZE = 30
TOP_N = 5


def _usernames(db, user_ids: set[str]) -> dict[str, str]:
    if not user_ids:
        return {}
    return dict(db.query(User.id, User.username).filter(User.id.in_(user_ids)).all())


@router.get("/overview")
def overview(_: AdminUser, db: DbSession, days: int = 7) -> dict:
    days = metrics.window_days(days)
    start = metrics.since(days)
    runs = metrics.runs_since(db, start)
    calls = metrics.calls_since(db, start)
    limit = get_settings().user_generation_limit

    per_user = Counter(r.user_id for r in runs)
    tokens_per_user = Counter()
    for r in runs:
        tokens_per_user[r.user_id] += r.prompt_tokens + r.completion_tokens
    names = _usernames(db, set(per_user))

    race_runs = [r for r in runs if r.race_lanes > 1]
    adopted = (
        db.query(func.count(Version.id))
        .filter(Version.created_at >= start, Version.source == "ai", Version.label.is_not(None))
        .scalar()
    )
    qa_checked = [r for r in runs if r.qa_ok is not None]
    coded_runs = {c.run_id for c in calls if c.agent == "alex"}
    fixed_runs = {c.run_id for c in calls if c.step.endswith("-fix")}

    shares = db.query(Share).order_by(Share.views.desc()).limit(TOP_N).all()
    share_titles = project_titles(db, {s.project_id for s in shares})

    return {
        "days": days,
        "users": {
            "total": db.query(func.count(User.id)).scalar(),
            "new": db.query(func.count(User.id)).filter(User.created_at >= start).scalar(),
            "active": len(per_user),
        },
        "projects": {
            "total": db.query(func.count(Project.id)).scalar(),
            "new": db.query(func.count(Project.id)).filter(Project.created_at >= start).scalar(),
        },
        "totals": metrics.run_totals(runs),
        "daily": metrics.daily(runs, days),
        "by_model": metrics.by_model(calls),
        "by_agent": metrics.by_agent(calls),
        "quality": {
            "qa_pass_rate": metrics.rate(sum(bool(r.qa_ok) for r in qa_checked), len(qa_checked)),
            "fix_rate": metrics.rate(len(fixed_runs), len(coded_runs)),
            "race_runs": len(race_runs),
            "race_adopted": adopted,
        },
        "top_users": [
            {"username": names.get(uid, uid), "runs": n, "tokens": tokens_per_user[uid]}
            for uid, n in per_user.most_common(TOP_N)
        ],
        "quota_alerts": [
            {"username": u.username, "used": u.generations_used, "limit": limit}
            for u in db.query(User)
            .filter(User.generations_used >= limit * 0.8)
            .order_by(User.generations_used.desc())
            .limit(10)
        ],
        "invites": [
            {"code": i.code, "used": i.used_count, "max": i.max_uses, "enabled": i.enabled}
            for i in db.query(InviteCode).order_by(InviteCode.created_at)
        ],
        "shares": {
            "total": db.query(func.count(Share.slug)).scalar(),
            "views_total": db.query(func.coalesce(func.sum(Share.views), 0)).scalar(),
            "views_window": db.query(func.count(ShareView.id))
            .filter(ShareView.created_at >= start)
            .scalar(),
            "top": [
                {"slug": s.slug, "title": share_titles.get(s.project_id), "views": s.views}
                for s in shares
            ],
        },
    }


@router.get("/runs")
def list_runs(
    _: AdminUser,
    db: DbSession,
    status: str | None = None,
    model: str | None = None,
    username: str | None = None,
    page: int = 1,
) -> dict:
    q = db.query(Run)
    if status:
        q = q.filter(Run.status == status)
    if model:
        q = q.filter(Run.id.in_(db.query(LLMCall.run_id).filter(LLMCall.model == model)))
    if username:
        user = db.query(User).filter(User.username == username.strip().lower()).first()
        q = q.filter(Run.user_id == (user.id if user else ""))
    total = q.count()
    page = max(1, page)
    rows = q.order_by(Run.created_at.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()
    titles = project_titles(db, {r.project_id for r in rows})
    names = _usernames(db, {r.user_id for r in rows})
    models = sorted({m for (m,) in db.query(LLMCall.model).distinct() if m})
    return {
        "total": total,
        "page": page,
        "page_size": PAGE_SIZE,
        "models": models,
        "items": [
            metrics.run_out(r, titles.get(r.project_id), names.get(r.user_id, "")) for r in rows
        ],
    }


@router.get("/runs/{run_id}")
def get_run(run_id: str, _: AdminUser, db: DbSession) -> dict:
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="运行记录不存在")
    titles = project_titles(db, {run.project_id})
    names = _usernames(db, {run.user_id})
    return {
        **metrics.run_out(run, titles.get(run.project_id), names.get(run.user_id, "")),
        "calls": [metrics.call_out(c, include_prompt=True) for c in run.calls],
    }
