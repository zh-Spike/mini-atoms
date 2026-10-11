import json
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.agents import tracing
from app.api import status as status_api
from app.config import get_settings
from app.db import SessionLocal
from app.models import LLMCall, Run, Version
from tests.conftest import register


def _events(resp) -> list[dict]:
    return [json.loads(line) for line in resp.text.splitlines() if line.strip()]


def _project(client: TestClient) -> str:
    return client.post("/api/projects", json={"prompt": "做一个待办清单"}).json()["id"]


def _send(client: TestClient, pid: str, content: str = "做一个待办清单", **body) -> list[dict]:
    return _events(client.post(f"/api/projects/{pid}/messages", json={"content": content, **body}))


def _calls(run_id: str) -> list[LLMCall]:
    tracing.flush()
    with SessionLocal() as db:
        return db.query(LLMCall).filter(LLMCall.run_id == run_id).order_by(LLMCall.started_at).all()


def _run(run_id: str) -> Run:
    tracing.flush()
    with SessionLocal() as db:
        run = db.get(Run, run_id)
        assert run is not None
        return run


@pytest.fixture
def usage_llm(fake_llm):
    fake_llm.model = "fake-1"
    fake_llm.last_usage = (10, 5)
    return fake_llm


@pytest.fixture
def as_admin(monkeypatch):
    def grant(client: TestClient) -> None:
        username = client.get("/api/auth/me").json()["username"]
        monkeypatch.setattr(get_settings(), "admin_usernames", username)

    return grant


def test_build_traces_every_agent_call(authed: TestClient, usage_llm) -> None:
    events = _send(authed, _project(authed))
    assert events[0]["type"] == "run_start"
    run_id = events[0]["run_id"]

    calls = _calls(run_id)
    assert [c.step for c in calls] == ["emma", "bob", "alex"]
    assert all(c.model == "fake-1" and c.status == "ok" for c in calls)
    assert calls[0].thinking == "思考一下"
    assert calls[0].messages[0]["role"] == "system" and calls[0].ttft_ms is not None
    assert "<file" in calls[2].output

    run = _run(run_id)
    assert (run.status, run.mode, run.qa_ok) == ("ok", "build", True)
    assert (run.prompt_tokens, run.completion_tokens) == (30, 15)
    assert run.version_id is not None and run.finished_at is not None

    done = events[-1]
    assert done["type"] == "done" and done["stats"]["tokens"] == 45
    assert [a["agent"] for a in done["stats"]["by_agent"]] == ["emma", "bob", "alex"]


def test_edit_traces_mike_and_fix_round(authed: TestClient, fake_llm) -> None:
    pid = _project(authed)
    _send(authed, pid)
    fake_llm.alex_replies = [
        '<file path="/App.js">\nimport X from "./components/X";\nexport default X;\n</file>',
        '<file path="/components/X.js">\nexport default () => null;\n</file>补上了组件',
    ]
    events = _send(authed, pid, "加一个组件")
    run_id = events[0]["run_id"]

    assert [c.step for c in _calls(run_id)] == ["mike", "alex", "alex-fix"]
    run = _run(run_id)
    assert (run.status, run.mode, run.qa_ok) == ("ok", "edit", True)


def test_race_lanes_are_traced(authed: TestClient, fake_llm) -> None:
    events = _send(authed, _project(authed), race=True)
    run_id = events[0]["run_id"]
    lanes = sorted(c.lane for c in _calls(run_id) if c.agent == "alex")
    assert lanes == [0, 1]
    assert _run(run_id).race_lanes == 2


def test_llm_failure_marks_run_and_call_as_error(authed: TestClient, fake_llm) -> None:
    async def broken(messages):
        raise RuntimeError("gateway exploded")
        yield  # pragma: no cover

    fake_llm.stream = broken
    events = _send(authed, _project(authed))
    assert events[-1]["type"] == "error"

    run_id = events[0]["run_id"]
    (call,) = _calls(run_id)
    assert (call.agent, call.status, call.error) == ("emma", "error", "gateway exploded")
    run = _run(run_id)
    assert run.status == "error" and "gateway exploded" in (run.error or "")


def test_trace_write_failure_does_not_break_generation(
    authed: TestClient, fake_llm, monkeypatch
) -> None:
    def broken_store(row) -> None:
        raise RuntimeError("database unreachable")

    monkeypatch.setattr(tracing, "store", broken_store)
    events = _send(authed, _project(authed))
    tracing.flush()
    assert any(e["type"] == "version" for e in events)
    assert events[-1]["type"] == "done"


def test_usage_and_run_detail_are_private(client: TestClient, usage_llm) -> None:
    client.cookies.clear()
    register(client)
    run_id = _send(client, _project(client))[0]["run_id"]
    tracing.flush()

    usage = client.get("/api/me/usage?days=30").json()
    assert usage["days"] == 30 and len(usage["daily"]) == 30
    assert usage["totals"]["runs"] == 1 and usage["totals"]["tokens"] == 45
    assert usage["quota"]["used"] == 1
    assert usage["recent"][0]["id"] == run_id
    assert usage["by_model"][0]["model"] == "fake-1"

    detail = client.get(f"/api/runs/{run_id}").json()
    assert len(detail["calls"]) == 3 and "messages" not in detail["calls"][0]

    client.cookies.clear()
    register(client)
    assert client.get(f"/api/runs/{run_id}").status_code == 404
    assert client.get("/api/me/usage").json()["totals"]["runs"] == 0


def test_admin_requires_admin(authed: TestClient) -> None:
    assert authed.get("/api/auth/me").json()["is_admin"] is False
    for url in ("/api/admin/overview", "/api/admin/runs", "/api/admin/runs/x"):
        assert authed.get(url).status_code == 403


def test_admin_overview_runs_and_trace(authed: TestClient, usage_llm, as_admin) -> None:
    run_id = _send(authed, _project(authed))[0]["run_id"]
    tracing.flush()
    as_admin(authed)
    assert authed.get("/api/auth/me").json()["is_admin"] is True

    overview = authed.get("/api/admin/overview").json()
    assert overview["totals"]["runs"] >= 1 and overview["users"]["active"] >= 1
    assert any(m["model"] == "fake-1" for m in overview["by_model"])
    assert {"qa_pass_rate", "fix_rate", "race_runs", "race_adopted"} <= set(overview["quality"])
    assert any(i["code"] == "TEST" for i in overview["invites"])

    page = authed.get("/api/admin/runs", params={"model": "fake-1", "status": "ok"}).json()
    assert run_id in [r["id"] for r in page["items"]] and "fake-1" in page["models"]
    assert authed.get("/api/admin/runs", params={"username": "nobody"}).json()["total"] == 0

    trace = authed.get(f"/api/admin/runs/{run_id}").json()
    assert trace["calls"][0]["messages"][0]["role"] == "system"


def test_race_adoptions_before_tracing_are_not_counted(
    authed: TestClient, fake_llm, as_admin
) -> None:
    pid = _project(authed)
    events = _send(authed, pid, race=True)
    tracing.flush()
    as_admin(authed)
    before = authed.get("/api/admin/overview").json()["quality"]["race_adopted"]

    with SessionLocal() as db:
        first_run = min(r.created_at for r in db.query(Run).all())
        db.add(
            Version(
                project_id=pid,
                number=99,
                files={"/App.js": "x"},
                source="ai",
                label="legacy-race",
                created_at=first_run - timedelta(minutes=1),
            )
        )
        db.commit()
    assert authed.get("/api/admin/overview").json()["quality"]["race_adopted"] == before

    candidate = next(e["version"]["id"] for e in events if e["type"] == "lane_done")
    authed.post(f"/api/versions/{candidate}/restore")
    assert authed.get("/api/admin/overview").json()["quality"]["race_adopted"] == before + 1


def test_status_is_public(client: TestClient, monkeypatch) -> None:
    async def gateway_up():
        return {"status": "up", "latency_ms": 12, "detail": ""}

    monkeypatch.setattr(status_api, "probe_gateway", gateway_up)
    monkeypatch.setitem(status_api._probe_cache, "result", None)
    client.cookies.clear()
    data = client.get("/api/status").json()
    assert data["status"] == "operational"
    assert [c["name"] for c in data["components"]] == ["app", "database", "llm_gateway"]
    assert len(data["hourly"]) == 24 and "version" in data
    assert "username" not in json.dumps(data)


def test_status_degraded_when_gateway_down(client: TestClient, monkeypatch) -> None:
    async def gateway_down():
        return {"status": "down", "latency_ms": None, "detail": "APITimeoutError"}

    monkeypatch.setattr(status_api, "probe_gateway", gateway_down)
    monkeypatch.setitem(status_api._probe_cache, "result", None)
    assert client.get("/api/status").json()["status"] == "degraded"


def test_share_views_are_recorded(authed: TestClient, fake_llm) -> None:
    pid = _project(authed)
    _send(authed, pid)
    slug = authed.post(f"/api/projects/{pid}/share").json()["slug"]

    iphone = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Mobile"}
    authed.get(f"/api/share/{slug}", params={"ref": "https://t.co/abc"}, headers=iphone)
    authed.get(f"/api/share/{slug}")

    stats = authed.get(f"/api/projects/{pid}/share/stats").json()
    assert stats["views_total"] == 2 and stats["views_window"] == 2
    assert sum(d["views"] for d in stats["daily"]) == 2
    assert {r["host"] for r in stats["referrers"]} == {"t.co", "直接访问"}
    assert {d["device"]: d["views"] for d in stats["devices"]} == {"mobile": 1, "desktop": 1}


def test_share_stats_requires_published_project(authed: TestClient) -> None:
    pid = _project(authed)
    assert authed.get(f"/api/projects/{pid}/share/stats").status_code == 404
