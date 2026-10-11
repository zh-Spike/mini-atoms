from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Literal, Protocol

from openai import AsyncOpenAI, BadRequestError

from app.agents.mock_llm import FallbackLLM, MockLLM
from app.config import get_settings

ChatMessages = list[dict[str, str]]
# "notice" carries a user-facing system note (e.g. the switch to demo mode), not model output.
ChunkKind = Literal["think", "text", "notice"]

MAX_RACE_LANES = 3

# Optional request params some models behind the gateway reject with a 400. Once a model rejects
# one, it is dropped for that model for the rest of the process. Tried in this order.
_OPTIONAL_PARAMS = ("extra_body", "reasoning_effort", "reasoning", "stream_options", "temperature")
_dropped: dict[str, set[str]] = {}
# Models found at runtime to only speak the Responses API.
_responses_detected: set[str] = set()

_REASONING_EVENTS = ("response.reasoning_text.delta", "response.reasoning_summary_text.delta")


class LLM(Protocol):
    def stream(self, messages: ChatMessages) -> AsyncIterator[tuple[ChunkKind, str]]:
        """Yield ("think", reasoning) and ("text", content) chunks as they arrive."""
        ...

    async def complete(self, messages: ChatMessages) -> str: ...


class _ProtocolNotSupported(Exception):
    pass


def _is_protocol_error(e: BadRequestError) -> bool:
    return "protocol_not_supported" in str(e)


class OpenAICompatLLM:
    """Chat Completions by default; Responses API for models configured or detected to need it."""

    def __init__(self, model: str | None = None, temperature: float = 0.4) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key or "missing",
            timeout=300,
            max_retries=4,
        )
        self._model = model or settings.llm_model
        self._temperature = temperature
        # Fast mode: DeepSeek-style `thinking` off, plus low reasoning effort for GLM / Grok,
        # which otherwise think for minutes before writing code.
        fast = settings.llm_disable_thinking
        self._extra = {"thinking": {"type": "disabled"}} if fast else None
        self._effort = "low" if fast else None
        configured = {m.strip() for m in settings.llm_responses_models.split(",") if m.strip()}
        self._configured_responses = self._model in configured
        self.tokens = 0
        # (prompt, completion) tokens of the most recent call, read by the tracer.
        self.last_usage = (0, 0)

    @property
    def model(self) -> str:
        return self._model

    @property
    def protocol(self) -> str:
        return "responses" if self._use_responses else "chat"

    @property
    def _use_responses(self) -> bool:
        return self._configured_responses or self._model in _responses_detected

    def _record(self, prompt: int | None, completion: int | None, total: int | None) -> None:
        prompt, completion = prompt or 0, completion or 0
        self.last_usage = (prompt, completion)
        self.tokens += total or prompt + completion

    async def _create(self, create, optional: dict, **kw):
        """On a 400, find the optional param the model rejects by leaving out one at a time."""
        dropped = _dropped.setdefault(self._model, set())
        extra = {k: v for k, v in optional.items() if v is not None and k not in dropped}

        async def attempt(params: dict):
            try:
                return await create(model=self._model, **kw, **params)
            except BadRequestError as e:
                if _is_protocol_error(e):
                    raise _ProtocolNotSupported from e
                raise

        try:
            return await attempt(extra)
        except BadRequestError:
            if not extra:
                raise
        for name in [p for p in _OPTIONAL_PARAMS if p in extra]:
            try:
                result = await attempt({k: v for k, v in extra.items() if k != name})
            except BadRequestError:
                continue
            dropped.add(name)
            return result
        result = await attempt({})
        dropped.update(extra)
        return result

    async def _chat(self, messages: ChatMessages, temperature: float, stream: bool):
        optional: dict = {"extra_body": self._extra, "reasoning_effort": self._effort}
        if stream:
            optional["stream_options"] = {"include_usage": True}
        return await self._create(
            self._client.chat.completions.create,
            optional,
            messages=messages,
            temperature=temperature,
            stream=stream,
        )

    async def _responses(self, messages: ChatMessages, temperature: float, stream: bool):
        return await self._create(
            self._client.responses.create,
            {
                "reasoning": {"effort": self._effort} if self._effort else None,
                "temperature": temperature,
            },
            input=messages,
            stream=stream,
        )

    async def stream(self, messages: ChatMessages) -> AsyncIterator[tuple[ChunkKind, str]]:
        self.last_usage = (0, 0)
        if not self._use_responses:
            try:
                resp = await self._chat(messages, self._temperature, stream=True)
            except _ProtocolNotSupported:
                _responses_detected.add(self._model)
            else:
                async for chunk in resp:
                    if chunk.usage:
                        u = chunk.usage
                        self._record(u.prompt_tokens, u.completion_tokens, u.total_tokens)
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    reasoning = (delta.model_extra or {}).get("reasoning_content")
                    if reasoning:
                        yield "think", reasoning
                    if delta.content:
                        yield "text", delta.content
                return

        events = await self._responses(messages, self._temperature, stream=True)
        async for ev in events:
            if ev.type == "response.output_text.delta":
                yield "text", ev.delta
            elif ev.type in _REASONING_EVENTS:
                yield "think", ev.delta
            elif ev.type == "response.completed" and ev.response.usage:
                u = ev.response.usage
                self._record(u.input_tokens, u.output_tokens, u.total_tokens)

    async def complete(self, messages: ChatMessages) -> str:
        self.last_usage = (0, 0)
        if not self._use_responses:
            try:
                resp = await self._chat(messages, 0.2, stream=False)
            except _ProtocolNotSupported:
                _responses_detected.add(self._model)
            else:
                if resp.usage:
                    u = resp.usage
                    self._record(u.prompt_tokens, u.completion_tokens, u.total_tokens)
                return resp.choices[0].message.content or ""

        resp = await self._responses(messages, 0.2, stream=False)
        if resp.usage:
            u = resp.usage
            self._record(u.input_tokens, u.output_tokens, u.total_tokens)
        return resp.output_text or ""


@dataclass
class RaceLane:
    label: str
    llm: LLM
    style: str = ""


RACE_STYLES = [
    ("稳健", 0.3, ""),
    (
        "创意",
        0.9,
        "\n\n风格要求：这一版请尝试更大胆的视觉设计（渐变背景、卡片层次、微动效），"
        "交互上可以加一两个让人眼前一亮的小细节，与常规方案拉开差异。",
    ),
]

RaceLaneFactory = Callable[[list[str]], list[RaceLane]]


def race_models() -> list[str]:
    """Models users may pick for a race; the default model is always included first."""
    settings = get_settings()
    configured = [m.strip() for m in settings.llm_race_models.split(",") if m.strip()]
    return list(dict.fromkeys([settings.llm_model, *configured]))


def build_race_lanes(models: list[str]) -> list[RaceLane]:
    """One lane per distinct model; fewer than two models races two styles of one model."""
    unique = list(dict.fromkeys(models))[:MAX_RACE_LANES]
    if len(unique) >= 2:
        return [RaceLane(m, OpenAICompatLLM(m)) for m in unique]
    model = unique[0] if unique else get_settings().llm_model
    return [
        RaceLane(f"{model} · {name}", OpenAICompatLLM(model, temp), style)
        for name, temp, style in RACE_STYLES
    ]


def demo_mode() -> bool:
    settings = get_settings()
    return settings.llm_mock or not settings.llm_api_key


def build_demo_race_lanes(models: list[str]) -> list[RaceLane]:
    unique = list(dict.fromkeys(models))[:MAX_RACE_LANES]
    if len(unique) >= 2:
        labels = [f"{m}（演示）" for m in unique]
    else:
        labels = ["演示 · 稳健", "演示 · 创意"]
    return [RaceLane(label, MockLLM(i, label)) for i, label in enumerate(labels)]


def _with_fallback(models: list[str]) -> list[RaceLane]:
    return [
        RaceLane(lane.label, FallbackLLM(lane.llm, MockLLM(i)), lane.style)
        for i, lane in enumerate(build_race_lanes(models))
    ]


def get_llm() -> LLM:
    return MockLLM() if demo_mode() else FallbackLLM(OpenAICompatLLM(), MockLLM())


def get_race_lanes() -> RaceLaneFactory:
    return build_demo_race_lanes if demo_mode() else _with_fallback
