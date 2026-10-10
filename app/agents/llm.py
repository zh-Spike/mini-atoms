from collections.abc import AsyncIterator
from typing import Literal, Protocol

from openai import AsyncOpenAI

from app.config import get_settings

ChatMessages = list[dict[str, str]]
ChunkKind = Literal["think", "text"]


class LLM(Protocol):
    def stream(self, messages: ChatMessages) -> AsyncIterator[tuple[ChunkKind, str]]:
        """Yield ("think", reasoning) and ("text", content) chunks as they arrive."""
        ...

    async def complete(self, messages: ChatMessages) -> str: ...


class OpenAICompatLLM:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(
            base_url=settings.llm_base_url, api_key=settings.llm_api_key or "missing", timeout=300
        )
        self._model = settings.llm_model
        self._extra = {"thinking": {"type": "disabled"}} if settings.llm_disable_thinking else None

    async def stream(self, messages: ChatMessages) -> AsyncIterator[tuple[ChunkKind, str]]:
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            stream=True,
            temperature=0.4,
            extra_body=self._extra,
        )
        async for chunk in resp:
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
        return resp.choices[0].message.content or ""


def get_llm() -> LLM:
    return OpenAICompatLLM()
