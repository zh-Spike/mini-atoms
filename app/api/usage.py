from fastapi import APIRouter, HTTPException

from app import metrics
from app.auth import CurrentUser, DbSession
from app.config import get_settings
from app.models import Project, Run

router = APIRouter(prefix="/api", tags=["usage"])

RECENT_RUNS = 20


def project_titles(db, project_ids: set[str]) -> dict[str, str]:
    if not project_ids:
        return {}
    rows = db.query(Project.id, Project.title).filter(Project.id.in_(project_ids)).all()
    return dict(rows)


@router.get("/me/usage")
def my_usage(user: CurrentUser, db: DbSession, days: int = 7) -> dict:
    days = metrics.window_days(days)
    runs = metrics.runs_since(db, metrics.since(days), user_id=user.id)
    calls = metrics.calls_since(db, metrics.since(days), [r.id for r in runs])
    recent = (
        db.query(Run)
        .filter(Run.user_id == user.id)
        .order_by(Run.created_at.desc())
        .limit(RECENT_RUNS)
        .all()
    )
    titles = project_titles(db, {r.project_id for r in recent})
    return {
        "days": days,
        "quota": {
            "used": user.generations_used,
            "limit": get_settings().user_generation_limit,
        },
        "totals": metrics.run_totals(runs),
        "daily": metrics.daily(runs, days),
        "by_model": metrics.by_model(calls),
        "by_agent": metrics.by_agent(calls),
        "recent": [metrics.run_out(r, titles.get(r.project_id)) for r in recent],
    }


@router.get("/runs/{run_id}")
def get_run(run_id: str, user: CurrentUser, db: DbSession) -> dict:
    run = db.get(Run, run_id)
    if run is None or run.user_id != user.id:
        raise HTTPException(status_code=404, detail="运行记录不存在")
    titles = project_titles(db, {run.project_id})
    return {
        **metrics.run_out(run, titles.get(run.project_id)),
        "calls": [metrics.call_out(c, include_prompt=False) for c in run.calls],
    }
