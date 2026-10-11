import json

import openai
import pytest
from fastapi.testclient import TestClient

from app.agents.llm import RaceLane, demo_mode, get_llm, get_race_lanes
from app.agents.mock_apps import APPS, app_files, pick_app
from app.agents.mock_llm import FallbackLLM, MockLLM
from app.agents.qa import check_project
from app.api import status as status_api
from app.config import get_settings
from app.main import app


def _events(resp) -> list[dict]:
    return [json.loads(line) for line in resp.text.splitlines() if line.strip()]


def _send(client: TestClient, pid: str, content: str, **body) -> list[dict]:
    resp = client.post(f"/api/projects/{pid}/messages", json={"content": content, **body})
    assert resp.status_code == 200
    return _events(resp)


def _project(client: TestClient, prompt: str) -> str:
    return client.post("/api/projects", json={"prompt": prompt}).json()["id"]


@pytest.fixture(autouse=True)
def no_api_key(monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "llm_api_key", "")


@pytest.fixture
def use_llm():
    def install(llm, lanes=None) -> None:
        app.dependency_overrides[get_llm] = lambda: llm
        if lanes is not None:
            app.dependency_overrides[get_race_lanes] = lambda: lanes

    yield install
    app.dependency_overrides.clear()


@pytest.mark.parametrize("mock_app", APPS, ids=lambda a: a.key)
@pytest.mark.parametrize(("accent", "fancy"), [("violet", False), ("emerald", True)])
def test_prebuilt_apps_pass_qa(mock_app, accent: str, fancy: bool) -> None:
    assert check_project(app_files(mock_app, accent, fancy)) == []


def test_pick_app_by_keyword() -> None:
    assert pick_app("做一个番茄钟").key == "pomodoro"
    assert pick_app("做一个记账本，按分类统计").key == "expense"
    assert pick_app("做一个 2048 小游戏").key == "kanban"


def test_no_api_key_means_demo_mode() -> None:
    assert demo_mode()
    assert isinstance(get_llm(), MockLLM)
    lanes = get_race_lanes()(["glm-5.3", "grok-4.7"])
    assert [lane.label for lane in lanes] == ["glm-5.3（演示）", "grok-4.7（演示）"]


def test_demo_mode_build_then_edit(authed: TestClient, use_llm) -> None:
    use_llm(MockLLM(delay=0))
    pid = _project(authed, "做一个番茄钟")

    events = _send(authed, pid, "做一个番茄钟")
    version = next(e for e in events if e["type"] == "version")["version"]
    assert {"/App.js", "/components/TimerDial.js", "/lib/theme.js"} <= set(version["files"])
    qa = [e for e in events if e["type"] == "agent_end" and e["agent"] == "qa"]
    assert [e["ok"] for e in qa] == [True]
    assert events[-1]["type"] == "done"

    events = _send(authed, pid, "把主色调换成蓝色")
    edited = next(e for e in events if e["type"] == "version")["version"]
    assert 'ACCENT = "blue"' in edited["files"]["/lib/theme.js"]
    assert edited["files"]["/App.js"] == version["files"]["/App.js"]

    assert authed.get("/api/models").json()["demo"] is True


def test_demo_race_lanes_differ(authed: TestClient, use_llm) -> None:
    lanes = [RaceLane("a", MockLLM(0, delay=0)), RaceLane("b", MockLLM(1, delay=0))]
    use_llm(MockLLM(delay=0), lambda models: lanes)
    pid = _project(authed, "做一个记账本")

    events = _send(authed, pid, "做一个记账本", race=True)
    themes = [e["version"]["files"]["/lib/theme.js"] for e in events if e["type"] == "lane_done"]
    assert len(themes) == 2 and themes[0] != themes[1]


class _DownLLM:
    model, protocol, tokens, last_usage = "real", "chat", 0, (0, 0)

    def _error(self) -> Exception:
        return openai.APIConnectionError(request=None)  # type: ignore[arg-type]

    async def stream(self, messages):
        raise self._error()
        yield  # pragma: no cover

    async def complete(self, messages) -> str:
        raise self._error()


def test_gateway_failure_falls_back_to_demo(authed: TestClient, use_llm) -> None:
    use_llm(FallbackLLM(_DownLLM(), MockLLM(delay=0)))
    pid = _project(authed, "做一个看板")

    events = _send(authed, pid, "做一个看板")
    notices = [e["text"] for e in events if e["type"] == "notice"]
    assert len(notices) == 1 and "无法连接模型网关" in notices[0]
    assert any(e["type"] == "version" for e in events)
    assert events[-1]["type"] == "done"


def test_status_reports_demo_gateway(client: TestClient, monkeypatch) -> None:
    monkeypatch.setitem(status_api._probe_cache, "result", None)
    data = client.get("/api/status").json()
    gateway = next(c for c in data["components"] if c["name"] == "llm_gateway")
    assert gateway["status"] == "demo"
    assert data["status"] == "operational"
