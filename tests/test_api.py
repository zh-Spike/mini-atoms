import json

from fastapi.testclient import TestClient

from tests.conftest import register


def _events(resp) -> list[dict]:
    return [json.loads(line) for line in resp.text.splitlines() if line.strip()]


def test_requires_login(client: TestClient) -> None:
    client.cookies.clear()
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/projects").status_code == 401


def test_invalid_and_exhausted_invite(client: TestClient) -> None:
    assert register(client, code="NOPE").status_code == 400
    assert register(client, code="ONCE").status_code == 200
    assert register(client, code="ONCE").status_code == 400


def test_register_validation(client: TestClient) -> None:
    def reg(username: str, password: str) -> int:
        body = {"invite_code": "TEST", "username": username, "password": password}
        return client.post("/api/auth/register", json=body).status_code

    assert reg("ab", "secret123") == 422
    assert reg("bad name", "secret123") == 422
    assert reg("shortpw", "123") == 422
    assert reg("Alice", "secret123") == 200
    assert reg("alice", "another1") == 409


def test_login_with_account(client: TestClient) -> None:
    client.cookies.clear()
    body = {"invite_code": "TEST", "username": "bob_1", "password": "secret123"}
    assert client.post("/api/auth/register", json=body).status_code == 200
    pid = client.post("/api/projects", json={"prompt": "待办清单"}).json()["id"]
    client.post("/api/auth/logout")
    client.cookies.clear()

    bad = client.post("/api/auth/login", json={"username": "bob_1", "password": "wrong"})
    assert bad.status_code == 401
    resp = client.post("/api/auth/login", json={"username": "BOB_1", "password": "secret123"})
    assert resp.status_code == 200 and resp.json()["username"] == "bob_1"
    assert client.get(f"/api/projects/{pid}").status_code == 200


def test_projects_are_isolated_per_user(authed: TestClient) -> None:
    pid = authed.post("/api/projects", json={"prompt": "待办清单"}).json()["id"]
    authed.cookies.clear()
    register(authed)
    assert authed.get(f"/api/projects/{pid}").status_code == 404


def test_build_then_edit_then_restore(authed: TestClient, fake_llm) -> None:
    pid = authed.post("/api/projects", json={"prompt": "做一个待办清单"}).json()["id"]

    events = _events(
        authed.post(f"/api/projects/{pid}/messages", json={"content": "做一个待办清单"})
    )
    starts = [e["agent"] for e in events if e["type"] == "agent_start"]
    assert starts == ["emma", "bob", "alex", "qa"]
    assert events[-1]["type"] == "done"
    v1 = next(e["version"] for e in events if e["type"] == "version")
    assert set(v1["files"]) == {"/App.js", "/components/Header.js"}

    fake_llm.alex_replies = [
        '<file path="/components/Header.js">\n'
        "export default () => <h1>新标题</h1>;\n</file>改了标题"
    ]
    events = _events(authed.post(f"/api/projects/{pid}/messages", json={"content": "改标题"}))
    starts = [e["agent"] for e in events if e["type"] == "agent_start"]
    assert starts == ["mike", "alex", "qa"]
    v2 = next(e["version"] for e in events if e["type"] == "version")
    assert v2["number"] == 2
    assert "新标题" in v2["files"]["/components/Header.js"]
    assert v2["files"]["/App.js"] == v1["files"]["/App.js"]

    restored = authed.post(f"/api/versions/{v1['id']}/restore").json()
    assert restored["number"] == 3 and restored["files"] == v1["files"]

    detail = authed.get(f"/api/projects/{pid}").json()
    assert detail["latest_version"]["number"] == 3
    assert [m["agent"] for m in detail["messages"] if m["role"] == "agent"][:4] == [
        "emma",
        "bob",
        "alex",
        "qa",
    ]


def test_qa_failure_triggers_one_fix(authed: TestClient, fake_llm) -> None:
    pid = authed.post("/api/projects", json={"prompt": "x"}).json()["id"]
    fake_llm.alex_replies = [
        '<file path="/App.js">\nimport X from "./components/X";\nexport default X;\n</file>',
        '<file path="/components/X.js">\nexport default () => null;\n</file>补上了组件',
    ]
    events = _events(authed.post(f"/api/projects/{pid}/messages", json={"content": "x"}))
    qa_results = [e["ok"] for e in events if e["type"] == "agent_end" and e["agent"] == "qa"]
    assert qa_results == [False, True]
    version = next(e["version"] for e in events if e["type"] == "version")
    assert "/components/X.js" in version["files"]


def test_markdown_fallback(authed: TestClient, fake_llm) -> None:
    pid = authed.post("/api/projects", json={"prompt": "x"}).json()["id"]
    fake_llm.alex_replies = [
        "实现如下：\n```jsx\nexport default function App() { return null; }\n```\n完成。"
    ]
    events = _events(authed.post(f"/api/projects/{pid}/messages", json={"content": "x"}))
    version = next(e["version"] for e in events if e["type"] == "version")
    assert list(version["files"]) == ["/App.js"]
    assert fake_llm.calls.count("alex") == 1
    assert any(e["type"] == "thinking" for e in events)


def test_retry_when_no_files(authed: TestClient, fake_llm) -> None:
    pid = authed.post("/api/projects", json={"prompt": "x"}).json()["id"]
    fake_llm.alex_replies = ["抱歉我只描述一下思路。"]
    events = _events(authed.post(f"/api/projects/{pid}/messages", json={"content": "x"}))
    assert fake_llm.calls.count("alex") == 2
    assert any(e["type"] == "version" for e in events)


def test_build_without_code_is_an_error(authed: TestClient, fake_llm) -> None:
    pid = authed.post("/api/projects", json={"prompt": "x"}).json()["id"]
    fake_llm.alex_replies = ["只有思路。", "还是只有思路。"]
    events = _events(authed.post(f"/api/projects/{pid}/messages", json={"content": "x"}))
    assert not any(e["type"] == "version" for e in events)
    error = next(e for e in events if e["type"] == "error")
    assert "没有产出代码" in error["message"]


def test_race_lane_without_code_reports_error(authed: TestClient, fake_llm) -> None:
    pid = authed.post("/api/projects", json={"prompt": "x"}).json()["id"]
    fake_llm.alex_replies = ["只有思路。", "还是只有思路。"]
    body = {"content": "x", "race": True}
    events = _events(authed.post(f"/api/projects/{pid}/messages", json=body))
    lane_errors = [e for e in events if e["type"] == "lane_error"]
    assert len(lane_errors) == 1 and "没有产出代码" in lane_errors[0]["message"]
    assert len([e for e in events if e["type"] == "lane_done"]) == 1
    assert events[-1]["type"] == "done"


def test_manual_version(authed: TestClient) -> None:
    pid = authed.post("/api/projects", json={"prompt": "x"}).json()["id"]
    v = authed.post(
        f"/api/projects/{pid}/versions", json={"files": {"/App.js": "export default 1;"}}
    ).json()
    assert v["source"] == "manual" and v["number"] == 1


def test_generation_limit(client: TestClient, fake_llm) -> None:
    client.cookies.clear()
    register(client)
    pid = client.post("/api/projects", json={"prompt": "x"}).json()["id"]
    codes = [
        client.post(f"/api/projects/{pid}/messages", json={"content": "x"}).status_code
        for _ in range(6)
    ]
    assert codes == [200] * 5 + [429]
