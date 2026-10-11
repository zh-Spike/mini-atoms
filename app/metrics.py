"""Aggregations behind the usage page, the operations dashboard and the status page.

Volumes are demo-sized, so rows in the window are loaded and aggregated in Python rather than
with dialect-specific SQL date functions (SQLite locally, Postgres in production).
"""

from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import LLMCall, Run

WINDOWS = (7, 30)


def aware(dt: datetime) -> datetime:
    """SQLite drops tzinfo; every stored timestamp is UTC."""
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def window_days(days: int) -> int:
    return days if days in WINDOWS else WINDOWS[0]


def since(days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


def _tz() -> ZoneInfo:
    return ZoneInfo(get_settings().stats_timezone)


def local_day(dt: datetime) -> date:
    return aware(dt).astimezone(_tz()).date()


def day_keys(days: int) -> list[date]:
    today = datetime.now(_tz()).date()
    return [today - timedelta(days=i) for i in range(days - 1, -1, -1)]


def percentile(values: Iterable[float], p: float) -> int | None:
    data = sorted(values)
    if not data:
        return None
    k = min(len(data) - 1, max(0, round(p / 100 * (len(data) - 1))))
    return int(data[k])


def rate(ok: int, total: int) -> float | None:
    return round(ok / total, 4) if total else None


def runs_since(db: Session, start: datetime, user_id: str | None = None) -> list[Run]:
    q = db.query(Run).filter(Run.created_at >= start)
    if user_id:
        q = q.filter(Run.user_id == user_id)
    return q.order_by(Run.created_at).all()


def calls_since(db: Session, start: datetime, run_ids: list[str] | None = None) -> list[LLMCall]:
    q = db.query(LLMCall).filter(LLMCall.started_at >= start)
    if run_ids is not None:
        if not run_ids:
            return []
        q = q.filter(LLMCall.run_id.in_(run_ids))
    return q.all()


def run_totals(runs: list[Run]) -> dict:
    status = Counter(r.status for r in runs)
    finished = status["ok"] + status["error"]
    return {
        "runs": len(runs),
        "ok": status["ok"],
        "error": status["error"],
        "aborted": status["aborted"],
        "running": status["running"],
        "success_rate": rate(status["ok"], finished),
        "tokens": sum(r.prompt_tokens + r.completion_tokens for r in runs),
        "prompt_tokens": sum(r.prompt_tokens for r in runs),
        "completion_tokens": sum(r.completion_tokens for r in runs),
        "p50_duration_ms": percentile((r.duration_ms for r in runs if r.status == "ok"), 50),
        "p95_duration_ms": percentile((r.duration_ms for r in runs if r.status == "ok"), 95),
    }


def daily(runs: list[Run], days: int) -> list[dict]:
    buckets: dict[date, dict] = {
        d: {"date": d.isoformat(), "runs": 0, "ok": 0, "error": 0, "tokens": 0, "users": set()}
        for d in day_keys(days)
    }
    for r in runs:
        b = buckets.get(local_day(r.created_at))
        if b is None:
            continue
        b["runs"] += 1
        b["ok"] += r.status == "ok"
        b["error"] += r.status == "error"
        b["tokens"] += r.prompt_tokens + r.completion_tokens
        b["users"].add(r.user_id)
    return [{**b, "users": len(b["users"])} for b in buckets.values()]


def by_model(calls: list[LLMCall]) -> list[dict]:
    groups: dict[str, list[LLMCall]] = defaultdict(list)
    for c in calls:
        groups[c.model or "unknown"].append(c)
    rows = []
    for model, cs in groups.items():
        errors = sum(c.status == "error" for c in cs)
        ttfts = [c.ttft_ms for c in cs if c.ttft_ms is not None and c.status == "ok"]
        rows.append(
            {
                "model": model,
                "calls": len(cs),
                "errors": errors,
                "success_rate": rate(len(cs) - errors, len(cs)),
                "avg_ttft_ms": int(sum(ttfts) / len(ttfts)) if ttfts else None,
                "p95_ttft_ms": percentile(ttfts, 95),
                "avg_duration_ms": int(sum(c.duration_ms for c in cs) / len(cs)),
                "tokens": sum(c.prompt_tokens + c.completion_tokens for c in cs),
            }
        )
    return sorted(rows, key=lambda r: -r["calls"])


AGENT_ORDER = ("mike", "emma", "bob", "alex")


def by_agent(calls: list[LLMCall]) -> list[dict]:
    groups: dict[str, list[LLMCall]] = defaultdict(list)
    for c in calls:
        groups[c.agent].append(c)
    rows = []
    for agent in sorted(groups, key=lambda a: AGENT_ORDER.index(a) if a in AGENT_ORDER else 9):
        cs = groups[agent]
        rows.append(
            {
                "agent": agent,
                "calls": len(cs),
                "tokens": sum(c.prompt_tokens + c.completion_tokens for c in cs),
                "avg_duration_ms": int(sum(c.duration_ms for c in cs) / len(cs)),
            }
        )
    return rows


def run_out(r: Run, project_title: str | None = None, username: str | None = None) -> dict:
    data = {
        "id": r.id,
        "project_id": r.project_id,
        "project_title": project_title,
        "mode": r.mode,
        "race_lanes": r.race_lanes,
        "status": r.status,
        "tokens": r.prompt_tokens + r.completion_tokens,
        "prompt_tokens": r.prompt_tokens,
        "completion_tokens": r.completion_tokens,
        "duration_ms": r.duration_ms,
        "qa_ok": r.qa_ok,
        "qa_issues": r.qa_issues or [],
        "version_id": r.version_id,
        "error": r.error,
        "created_at": aware(r.created_at).isoformat(),
    }
    if username is not None:
        data["username"] = username
    return data


def call_out(c: LLMCall, include_prompt: bool) -> dict:
    data = {
        "id": c.id,
        "agent": c.agent,
        "step": c.step,
        "lane": c.lane,
        "model": c.model,
        "protocol": c.protocol,
        "thinking": c.thinking,
        "output": c.output,
        "prompt_tokens": c.prompt_tokens,
        "completion_tokens": c.completion_tokens,
        "ttft_ms": c.ttft_ms,
        "duration_ms": c.duration_ms,
        "status": c.status,
        "error": c.error,
        "started_at": aware(c.started_at).isoformat(),
    }
    if include_prompt:
        data["messages"] = c.messages
    return data
