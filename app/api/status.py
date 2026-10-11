"""Public service status: no user data, safe to open without logging in."""

import asyncio
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from openai import AsyncOpenAI
from sqlalchemy import text

from app import metrics
from app.agents.llm import demo_mode
from app.config import get_settings
from app.db import SessionLocal

router = APIRouter(prefix="/api", tags=["status"])

STARTED_AT = time.time()
PROBE_TTL_S = 60
PROBE_TIMEOUT_S = 5
# Below this 24h success rate (with enough runs to judge) the service shows as degraded.
DEGRADED_SUCCESS_RATE = 0.8
MIN_RUNS_TO_JUDGE = 5

_probe_cache: dict = {"at": 0.0, "result": None}


async def probe_gateway() -> dict:
    settings = get_settings()
    if demo_mode():
        return {"status": "demo", "latency_ms": None, "detail": "未接入模型，使用预置结果"}
    client = AsyncOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        timeout=PROBE_TIMEOUT_S,
        max_retries=0,
    )
    started = time.monotonic()
    try:
        await client.models.list()
    except Exception as exc:
        return {"status": "down", "latency_ms": None, "detail": type(exc).__name__}
    return {"status": "up", "latency_ms": int((time.monotonic() - started) * 1000), "detail": ""}


async def _cached_probe() -> dict:
    now = time.monotonic()
    if _probe_cache["result"] is None or now - _probe_cache["at"] > PROBE_TTL_S:
        _probe_cache["result"] = await probe_gateway()
        _probe_cache["at"] = now
    return _probe_cache["result"]


def _db_report() -> tuple[dict, list, list]:
    """Database health plus the last 24h of runs and per-model stats; blocking, run in a thread."""
    with SessionLocal() as db:
        started = time.monotonic()
        try:
            db.execute(text("SELECT 1"))
        except Exception as exc:
            return {"status": "down", "latency_ms": None, "detail": type(exc).__name__}, [], []
        latency = int((time.monotonic() - started) * 1000)
        start = datetime.now(UTC) - timedelta(hours=24)
        runs = metrics.runs_since(db, start)
        models = [
            {k: m[k] for k in ("model", "calls", "errors", "success_rate", "avg_ttft_ms")}
            for m in metrics.by_model(metrics.calls_since(db, start))
        ]
    return {"status": "up", "latency_ms": latency, "detail": ""}, runs, models


def _hourly(runs) -> list[dict]:
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    hours = [now - timedelta(hours=i) for i in range(23, -1, -1)]
    buckets = defaultdict(lambda: {"ok": 0, "error": 0})
    for r in runs:
        hour = metrics.aware(r.created_at).replace(minute=0, second=0, microsecond=0)
        if r.status in ("ok", "error"):
            buckets[hour][r.status] += 1
    return [{"hour": h.isoformat(), **buckets[h]} for h in hours]


@router.get("/status")
async def status() -> dict:
    (database, runs, models), gateway = await asyncio.gather(
        asyncio.to_thread(_db_report), _cached_probe()
    )
    totals = metrics.run_totals(runs)

    if database["status"] != "up":
        overall = "down"
    elif gateway["status"] == "down" or (
        totals["success_rate"] is not None
        and totals["ok"] + totals["error"] >= MIN_RUNS_TO_JUDGE
        and totals["success_rate"] < DEGRADED_SUCCESS_RATE
    ):
        overall = "degraded"
    else:
        overall = "operational"

    return {
        "status": overall,
        "version": get_settings().git_sha,
        "uptime_s": int(time.time() - STARTED_AT),
        "checked_at": datetime.now(UTC).isoformat(),
        "components": [
            {"name": "app", "status": "up", "latency_ms": None, "detail": ""},
            {"name": "database", **database},
            {"name": "llm_gateway", **gateway},
        ],
        "runs_24h": {
            k: totals[k] for k in ("runs", "ok", "error", "success_rate", "p50_duration_ms")
        },
        "hourly": _hourly(runs),
        "models_24h": models,
    }
