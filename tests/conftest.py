import os
import tempfile
import uuid
from collections.abc import AsyncIterator, Iterator

_db_dir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_db_dir}/test.db"
os.environ["INVITE_CODES"] = "TEST:100,ONCE:1"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["USER_GENERATION_LIMIT"] = "5"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.agents import prompts  # noqa: E402
from app.agents.llm import get_llm  # noqa: E402
from app.main import app  # noqa: E402

APP_JS = (
    'import Header from "./components/Header";\n'
    "export default function App() {\n  return <Header />;\n}\n"
)
HEADER_JS = "export default function Header() {\n  return <h1>Hi</h1>;\n}\n"


class FakeLLM:
    """Replies by role, recognised from the system prompt. Chunks are tiny to stress the parser."""

    def __init__(self) -> None:
        self.route = '{"mode": "edit", "reply": "交给 Alex 修改"}'
        self.alex_replies: list[str] = []
        self.calls: list[str] = []

    def _reply(self, system: str) -> str:
        if system == prompts.EMMA_PRD:
            self.calls.append("emma")
            return "## 产品目标\n一个示例应用"
        if system == prompts.BOB_DESIGN:
            self.calls.append("bob")
            return "## 文件结构\n- /App.js"
        self.calls.append("alex")
        if self.alex_replies:
            return self.alex_replies.pop(0)
        return (
            f'<file path="/App.js">\n{APP_JS}</file>\n'
            f'<file path="/components/Header.js">\n{HEADER_JS}</file>\n完成了示例应用。'
        )

    async def stream(self, messages) -> AsyncIterator[tuple[str, str]]:
        yield "think", "思考一下"
        text = self._reply(messages[0]["content"])
        for i in range(0, len(text), 7):
            yield "text", text[i : i + 7]

    async def complete(self, messages) -> str:
        self.calls.append("mike")
        return self.route


@pytest.fixture
def fake_llm() -> Iterator[FakeLLM]:
    llm = FakeLLM()
    app.dependency_overrides[get_llm] = lambda: llm
    yield llm
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


def register(client: TestClient, code: str = "TEST", password: str = "secret123"):
    username = f"u{uuid.uuid4().hex[:12]}"
    return client.post(
        "/api/auth/register",
        json={"invite_code": code, "username": username, "password": password},
    )


@pytest.fixture
def authed(client: TestClient) -> TestClient:
    client.cookies.clear()
    resp = register(client)
    assert resp.status_code == 200
    return client
