import asyncio
from types import SimpleNamespace

import httpx2
from openai import BadRequestError

from app.agents import llm as llm_module
from app.agents.llm import OpenAICompatLLM, build_race_lanes

MSG = [{"role": "user", "content": "hi"}]


def _bad_request(message: str = "unsupported parameter") -> BadRequestError:
    response = httpx2.Response(400, request=httpx2.Request("POST", "http://test/v1"))
    return BadRequestError(message, response=response, body=None)


class _Endpoint:
    """Records calls; raises `error` for requests carrying any of `rejected` params."""

    def __init__(self, reply, rejected=(), error: BadRequestError | None = None) -> None:
        self.reply, self.rejected, self.error = reply, set(rejected), error
        self.calls: list[set[str]] = []

    async def create(self, **kw):
        self.calls.append(set(kw))
        if self.error is not None:
            raise self.error
        if self.rejected & set(kw):
            raise _bad_request()
        return self.reply


def _chat_reply(text: str = "ok"):
    message = SimpleNamespace(content=text)
    return SimpleNamespace(usage=None, choices=[SimpleNamespace(message=message)])


def _llm(model: str, chat: _Endpoint, responses: _Endpoint | None = None) -> OpenAICompatLLM:
    llm = OpenAICompatLLM(model)
    responses = responses or _Endpoint(SimpleNamespace(usage=None, output_text="via responses"))
    llm._client = SimpleNamespace(chat=SimpleNamespace(completions=chat), responses=responses)
    return llm


def _reset(monkeypatch) -> None:
    monkeypatch.setattr(llm_module, "_dropped", {})
    monkeypatch.setattr(llm_module, "_responses_detected", set())


def test_drops_rejected_params_per_model(monkeypatch) -> None:
    _reset(monkeypatch)
    chat = _Endpoint(_chat_reply(), rejected={"extra_body"})
    assert asyncio.run(_llm("model-x", chat).complete(MSG)) == "ok"
    assert "extra_body" in chat.calls[0] and "extra_body" not in chat.calls[1]

    chat = _Endpoint(_chat_reply(), rejected={"extra_body"})
    asyncio.run(_llm("model-x", chat).complete(MSG))
    assert len(chat.calls) == 1

    chat = _Endpoint(_chat_reply())
    asyncio.run(_llm("model-y", chat).complete(MSG))
    assert "extra_body" in chat.calls[0]


def test_only_the_rejected_param_is_dropped(monkeypatch) -> None:
    _reset(monkeypatch)
    chat = _Endpoint(_chat_reply(), rejected={"reasoning_effort"})
    asyncio.run(_llm("model-r", chat).complete(MSG))
    assert llm_module._dropped["model-r"] == {"reasoning_effort"}
    assert "extra_body" in chat.calls[-1]

    _reset(monkeypatch)
    chat = _Endpoint(_chat_reply(), rejected={"reasoning_effort", "extra_body"})
    asyncio.run(_llm("model-s", chat).complete(MSG))
    assert llm_module._dropped["model-s"] == {"reasoning_effort", "extra_body"}
    assert "max_tokens" in chat.calls[-1]


def test_output_cap_is_sent(monkeypatch) -> None:
    _reset(monkeypatch)
    chat = _Endpoint(_chat_reply())
    responses = _Endpoint(SimpleNamespace(usage=None, output_text="r"))
    asyncio.run(_llm("model-cap", chat).complete(MSG))
    asyncio.run(_llm("grok-4.7", chat, responses).complete(MSG))
    assert "max_tokens" in chat.calls[0] and "max_output_tokens" in responses.calls[0]


def test_switches_to_responses_on_protocol_error(monkeypatch) -> None:
    _reset(monkeypatch)
    chat = _Endpoint(_chat_reply(), error=_bad_request("protocol_not_supported"))
    assert asyncio.run(_llm("model-z", chat).complete(MSG)) == "via responses"
    assert len(chat.calls) == 1

    chat = _Endpoint(_chat_reply())
    assert asyncio.run(_llm("model-z", chat).complete(MSG)) == "via responses"
    assert chat.calls == []


def test_configured_responses_models(monkeypatch) -> None:
    _reset(monkeypatch)
    chat = _Endpoint(_chat_reply())
    responses = _Endpoint(SimpleNamespace(usage=None, output_text="r"))
    assert asyncio.run(_llm("grok-4.7", chat, responses).complete(MSG)) == "r"
    assert chat.calls == [] and "input" in responses.calls[0]


def test_build_race_lanes() -> None:
    lanes = build_race_lanes(["glm-5.3", "grok-4.7", "glm-5.3"])
    assert [lane.label for lane in lanes] == ["glm-5.3", "grok-4.7"]
    styles = build_race_lanes([])
    assert [lane.label for lane in styles] == ["deepseek-flash · 稳健", "deepseek-flash · 创意"]
