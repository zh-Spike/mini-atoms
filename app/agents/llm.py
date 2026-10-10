from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Literal, Protocol

from openai import AsyncOpenAI, BadRequestError

from app.config import get_settings

ChatMessages = list[dict[str, str]]
ChunkKind = Literal["think", "text"]

MAX_RACE_LANES = 3

# Optional request params some models behind the gateway reject with a 400. Once a model rejects
# one, it is dropped for that model for the rest of the process. Tried in this order.
_OPTIONAL_PARAMS = ("stream_options", "extra_body")
_dropped: dict[str, set[str]] = {}


class LLM(Protocol):
    def stream(self, messages: ChatMessages) -> AsyncIterator[tuple[ChunkKind, str]]:
        """Yield ("think", reasoning) and ("text", content) chunks as they arrive."""
        ...

    async def complete(self, messages: ChatMessages) -> str: ...


class OpenAICompatLLM:
    def __init__(self, model: str | None = None, temperature: float = 0.4) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(
            base_url=settings.llm_base_url, api_key=settings.llm_api_key or "missing", timeout=300
        )
        self._model = model or settings.llm_model
        self._temperature = temperature
        self._extra = {"thinking": {"type": "disabled"}} if settings.llm_disable_thinking else None
        self.tokens = 0

    async def _create(self, **kw):
        optional = {"extra_body": self._extra}
        if kw.get("stream"):
            optional["stream_options"] = {"include_usage": True}
        dropped = _dropped.setdefault(self._model, set())
        while True:
            extra = {k: v for k, v in optional.items() if v is not None and k not in dropped}
            try:
                return await self._client.chat.completions.create(model=self._model, **kw, **extra)
            except BadRequestError:
                droppable = [p for p in _OPTIONAL_PARAMS if p in extra]
                if not droppable:
                    raise
                dropped.add(droppable[0])

    async def stream(self, messages: ChatMessages) -> AsyncIterator[tuple[ChunkKind, str]]:
        resp = await self._create(messages=messages, stream=True, temperature=self._temperature)
        async for chunk in resp:
            if chunk.usage:
                self.tokens += chunk.usage.total_tokens or 0
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            reasoning = (delta.model_extra or {}).get("reasoning_content")
            if reasoning:
                yield "think", reasoning
            if delta.content:
                yield "text", delta.content

    async def complete(self, messages: ChatMessages) -> str:
        resp = await self._create(messages=messages, temperature=0.2)
        if resp.usage:
            self.tokens += resp.usage.total_tokens or 0
        return resp.choices[0].message.content or ""


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


def get_llm() -> LLM:
    return OpenAICompatLLM()


def get_race_lanes() -> RaceLaneFactory:
    return build_race_lanes
