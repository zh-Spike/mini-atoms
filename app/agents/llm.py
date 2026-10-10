from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, Protocol

from openai import AsyncOpenAI, BadRequestError

from app.config import get_settings

ChatMessages = list[dict[str, str]]
ChunkKind = Literal["think", "text"]

# Some OpenAI-compatible providers reject `stream_options`; stop sending it after the first 400.
_usage_supported = True


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

    async def _create_stream(self, messages: ChatMessages):
        kw = {
            "model": self._model,
            "messages": messages,
            "stream": True,
            "temperature": self._temperature,
            "extra_body": self._extra,
        }
        global _usage_supported
        if _usage_supported:
            try:
                return await self._client.chat.completions.create(
                    **kw, stream_options={"include_usage": True}
                )
            except BadRequestError:
                _usage_supported = False
        return await self._client.chat.completions.create(**kw)

    async def stream(self, messages: ChatMessages) -> AsyncIterator[tuple[ChunkKind, str]]:
        resp = await self._create_stream(messages)
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
        resp = await self._client.chat.completions.create(
            model=self._model, messages=messages, temperature=0.2, extra_body=self._extra
        )
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


def get_llm() -> LLM:
    return OpenAICompatLLM()


def get_race_lanes() -> list[RaceLane]:
    settings = get_settings()
    models = [m.strip() for m in settings.llm_race_models.split(",") if m.strip()]
    if len(models) >= 2:
        return [RaceLane(m, OpenAICompatLLM(m)) for m in models[:3]]
    model = models[0] if models else settings.llm_model
    return [
        RaceLane(f"{model} · {name}", OpenAICompatLLM(model, temp), style)
        for name, temp, style in RACE_STYLES
    ]
