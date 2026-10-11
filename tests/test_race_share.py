import json

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text

from tests.conftest import register


def _events(resp) -> list[dict]:
    return [json.loads(line) for line in resp.text.splitlines() if line.strip()]


def _new_project(client: TestClient) -> str:
    return client.post("/api/projects", json={"prompt": "做一个待办清单"}).json()["id"]


def _build(client: TestClient, pid: str, **body) -> list[dict]:
    resp = client.post(f"/api/projects/{pid}/messages", json={"content": "做一个待办清单", **body})
    return _events(resp)


def test_race_produces_candidates_and_adopt(authed: TestClient, fake_llm) -> None:
    pid = _new_project(authed)
    events = _build(authed, pid, race=True)

    assert [e["type"] for e in events[:2]] == ["run_start", "user_message"]
    assert events[2]["type"] == "agent_start" and events[2]["agent"] == "emma"
    race_start = next(e for e in events if e["type"] == "race_start")
    assert race_start["lanes"] == ["fake · 稳健", "fake · 创意"]
    assert {e["lane"] for e in events if e["type"] == "file_start"} == {0, 1}
    assert sorted(e["lane"] for e in events if e["type"] == "lane_finished") == [0, 1]
    assert fake_llm.calls.count("emma") == 1 and fake_llm.calls.count("alex") == 2

    lane_done = [e for e in events if e["type"] == "lane_done"]
    assert [e["version"]["source"] for e in lane_done] == ["race", "race"]
    assert [e["version"]["label"] for e in lane_done] == ["fake · 稳健", "fake · 创意"]
    assert all(e["message"]["version_id"] == e["version"]["id"] for e in lane_done)
    race_done = next(e for e in events if e["type"] == "race_done")
    assert race_done["version_ids"] == [e["version"]["id"] for e in lane_done]
    assert events[-1]["type"] == "done" and "duration_ms" in events[-1]["stats"]

    assert authed.get("/api/auth/me").json()["generations_used"] == 2

    adopted = authed.post(f"/api/versions/{race_done['version_ids'][0]}/restore").json()
    assert adopted["source"] == "ai" and adopted["label"] == "fake · 稳健"
    detail = authed.get(f"/api/projects/{pid}").json()
    assert detail["latest_version"]["id"] == adopted["id"]
    assert detail["latest_version"]["number"] == 3


def test_models_endpoint(authed: TestClient) -> None:
    data = authed.get("/api/models").json()
    assert data["race_models"] == ["deepseek-flash", "glm-5.3-flashx", "glm-5.3", "grok-4.7"]
    assert data["default"] == "deepseek-flash" and data["max_race_lanes"] == 3


def test_race_with_picked_models(authed: TestClient, fake_llm) -> None:
    pid = _new_project(authed)
    models = ["glm-5.3-flashx", "glm-5.3", "grok-4.7"]
    events = _build(authed, pid, race=True, race_models=models)
    assert next(e for e in events if e["type"] == "race_start")["lanes"] == models
    labels = [e["version"]["label"] for e in events if e["type"] == "lane_done"]
    assert labels == models
    assert authed.get("/api/auth/me").json()["generations_used"] == 3


def test_race_model_validation(authed: TestClient, fake_llm) -> None:
    pid = _new_project(authed)
    bad = _build_status(authed, pid, race=True, race_models=["glm-5.3", "gpt-unknown"])
    assert bad == 400
    assert _build_status(authed, pid, race=True, race_models=["glm-5.3"]) == 400
    assert _build_status(authed, pid, race=True, race_models=["a", "b", "c", "d"]) == 422
    assert authed.get("/api/auth/me").json()["generations_used"] == 0


def _build_status(client: TestClient, pid: str, **body) -> int:
    resp = client.post(f"/api/projects/{pid}/messages", json={"content": "x", **body})
    return resp.status_code


def test_race_ignored_for_edits(authed: TestClient, fake_llm) -> None:
    pid = _new_project(authed)
    _build(authed, pid)
    events = _build(authed, pid, race=True)
    assert not any(e["type"] == "race_start" for e in events)
    assert any(e["type"] == "version" for e in events)
    assert authed.get("/api/auth/me").json()["generations_used"] == 2


def test_race_falls_back_without_quota(client: TestClient, fake_llm) -> None:
    client.cookies.clear()
    register(client)
    pid = _new_project(client)
    for _ in range(4):
        _build(client, pid)
    fake_llm.route = '{"mode": "rebuild", "reply": "重做"}'
    events = _build(client, pid, race=True)
    assert any(e["type"] == "notice" for e in events)
    assert not any(e["type"] == "race_start" for e in events)
    assert any(e["type"] == "version" for e in events)
    assert client.get("/api/auth/me").json()["generations_used"] == 5


def test_share_lifecycle(authed: TestClient, fake_llm) -> None:
    pid = _new_project(authed)
    assert authed.post(f"/api/projects/{pid}/share").status_code == 400

    _build(authed, pid)
    share = authed.post(f"/api/projects/{pid}/share").json()
    assert share["version_number"] == 1 and share["views"] == 0
    assert authed.get(f"/api/projects/{pid}").json()["share"]["slug"] == share["slug"]

    authed.post(f"/api/projects/{pid}/versions", json={"files": {"/App.js": "export default 1;"}})
    updated = authed.post(f"/api/projects/{pid}/share").json()
    assert updated["slug"] == share["slug"] and updated["version_number"] == 2

    authed.cookies.clear()
    public = authed.get(f"/api/share/{share['slug']}").json()
    assert public["files"] == {"/App.js": "export default 1;"}
    assert public["title"] == "做一个待办清单"
    assert authed.get(f"/api/share/{share['slug']}").json()["views"] == 2

    register(authed)
    assert authed.post(f"/api/projects/{pid}/share").status_code == 404
    assert authed.delete(f"/api/projects/{pid}/share").status_code == 404


def test_unpublish_and_delete_project(authed: TestClient, fake_llm) -> None:
    pid = _new_project(authed)
    _build(authed, pid)
    slug = authed.post(f"/api/projects/{pid}/share").json()["slug"]
    assert authed.delete(f"/api/projects/{pid}/share").status_code == 200
    assert authed.get(f"/api/share/{slug}").status_code == 404
    assert authed.get(f"/api/projects/{pid}").json()["share"] is None

    slug = authed.post(f"/api/projects/{pid}/share").json()["slug"]
    assert authed.delete(f"/api/projects/{pid}").status_code == 200
    assert authed.get(f"/api/share/{slug}").status_code == 404


def test_add_missing_columns(tmp_path, monkeypatch) -> None:
    from app import db

    engine = create_engine(f"sqlite:///{tmp_path}/old.db")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE versions (id VARCHAR(32) PRIMARY KEY)"))
    monkeypatch.setattr(db, "engine", engine)
    db._add_missing_columns()
    db._add_missing_columns()
    assert "label" in {c["name"] for c in inspect(engine).get_columns("versions")}
