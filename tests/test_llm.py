import asyncio
from types import SimpleNamespace

import httpx2
from openai import BadRequestError

from app.agents import llm as llm_module
from app.agents.llm import OpenAICompatLLM, build_race_lanes


def _bad_request() -> BadRequestError:
    response = httpx2.Response(400, request=httpx2.Request("POST", "http://test/v1"))
    return BadRequestError("unsupported parameter", response=response, body=None)


class _Completions:
    """Rejects any request that carries one of `rejected` params."""

    def __init__(self, rejected: set[str]) -> None:
        self.rejected = rejected
        self.calls: list[set[str]] = []

    async def create(self, **kw):
        self.calls.append(set(kw))
        if self.rejected & set(kw):
            raise _bad_request()
        message = SimpleNamespace(content="ok")
        return SimpleNamespace(usage=None, choices=[SimpleNamespace(message=message)])


def _llm_with(rejected: set[str], model: str) -> tuple[OpenAICompatLLM, _Completions]:
    llm = OpenAICompatLLM(model)
    completions = _Completions(rejected)
    llm._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return llm, completions


def test_drops_rejected_params_per_model(monkeypatch) -> None:
    monkeypatch.setattr(llm_module, "_dropped", {})
    llm, calls = _llm_with({"extra_body"}, "grok-4.7")
    assert asyncio.run(llm.complete([{"role": "user", "content": "hi"}])) == "ok"
    assert "extra_body" in calls.calls[0] and "extra_body" not in calls.calls[1]

    again, calls = _llm_with({"extra_body"}, "grok-4.7")
    asyncio.run(again.complete([{"role": "user", "content": "hi"}]))
    assert len(calls.calls) == 1

    other, calls = _llm_with(set(), "glm-5.3")
    asyncio.run(other.complete([{"role": "user", "content": "hi"}]))
    assert "extra_body" in calls.calls[0]


def test_build_race_lanes() -> None:
    lanes = build_race_lanes(["glm-5.3", "grok-4.7", "glm-5.3"])
    assert [lane.label for lane in lanes] == ["glm-5.3", "grok-4.7"]
    styles = build_race_lanes([])
    assert [lane.label for lane in styles] == ["deepseek-flash · 稳健", "deepseek-flash · 创意"]
