"""Demo mode: a stand-in LLM that replays prebuilt apps, so the whole flow works without a model.

`MockLLM` is used when no API key is configured (or `LLM_MOCK=true`). `FallbackLLM` wraps the real
client and switches to `MockLLM` for the rest of the run if the gateway is unreachable, rejects the
key or is out of quota, so a demo never dead-ends on a provider outage.
"""

import asyncio
import json
from collections.abc import AsyncIterator

import openai

from app.agents import prompts
from app.agents.mock_apps import (
    DEFAULT_ACCENT,
    LANE_ACCENTS,
    app_files,
    current_theme,
    pick_app,
    requested_accent,
    theme_js,
)

MOCK_MODEL = "demo"
DEMO_NOTICE = "模型服务暂时不可用（{reason}），本轮改用演示模式的预置结果。"
FALLBACK_ERRORS = (
    openai.APIConnectionError,
    openai.AuthenticationError,
    openai.PermissionDeniedError,
    openai.RateLimitError,
    openai.InternalServerError,
)
CHUNK = 24


def _after(text: str, marker: str) -> str:
    _, _, rest = text.partition(marker)
    return (rest or text).split("\n\n")[0]


class MockLLM:
    """Recognises the agent from its system prompt and replies with prebuilt content.

    `variant` picks the race lane look: lane 0 is the light theme, odd lanes the dark one, and each
    lane gets its own accent colour.
    """

    protocol = "mock"

    def __init__(self, variant: int = 0, label: str = MOCK_MODEL, delay: float = 0.01) -> None:
        self.variant, self._label, self._delay = variant, label, delay
        self.tokens = 0
        self.last_usage = (0, 0)

    @property
    def model(self) -> str:
        return self._label

    def _accent(self) -> str:
        return LANE_ACCENTS[self.variant % len(LANE_ACCENTS)] if self.variant else DEFAULT_ACCENT

    def _reply(self, messages) -> str:
        system, user = messages[0]["content"], messages[-1]["content"]
        if system == prompts.EMMA_PRD:
            return pick_app(user).prd
        if system == prompts.BOB_DESIGN:
            return pick_app(_after(user, "用户需求：")).design
        if system == prompts.ALEX_BUILD:
            app = pick_app(_after(user, "用户需求："))
            files = app_files(app, self._accent(), fancy=self.variant % 2 == 1)
            body = "".join(f'<file path="{p}">\n{c}</file>\n' for p, c in files.items())
            return body + app.summary
        if system == prompts.ALEX_EDIT:
            return self._edit(user)
        return "演示模式下没有可执行的修复，请配置模型后重试。"

    def _edit(self, user: str) -> str:
        """Only theme edits are prebuilt: a named colour, otherwise a light / dark switch."""
        accent, fancy = current_theme(user)
        wanted = requested_accent(_after(user, "用户的修改要求："))
        if wanted:
            summary = f"已把主色调换成 {wanted}，按钮、标签和图表都会跟着变化。"
            accent = wanted
        else:
            fancy = not fancy
            summary = (
                f"演示模式只预置了主题修改，已切换为{'深色' if fancy else '浅色'}外观。"
                "可以试试“把主色调换成蓝色”；配置 LLM_API_KEY 后可以做任意修改。"
            )
        return f'<file path="/lib/theme.js">\n{theme_js(accent, fancy)}</file>\n{summary}'

    async def stream(self, messages) -> AsyncIterator[tuple[str, str]]:
        self.last_usage = (0, 0)
        yield "think", "演示模式：使用预置结果。"
        text = self._reply(messages)
        for i in range(0, len(text), CHUNK):
            if self._delay:
                await asyncio.sleep(self._delay)
            yield "text", text[i : i + CHUNK]

    async def complete(self, messages) -> str:
        self.last_usage = (0, 0)
        text = _after(messages[-1]["content"], "用户消息：")
        if any(k in text for k in ("重做", "重新做", "做一个", "换一个")):
            return json.dumps(
                {"mode": "rebuild", "reply": "这是一个新应用，我让 Emma 重新梳理需求。"},
                ensure_ascii=False,
            )
        return json.dumps(
            {"mode": "edit", "reply": "收到，我让 Alex 在现有应用上修改。"}, ensure_ascii=False
        )


def _reason(exc: Exception) -> str:
    if isinstance(exc, openai.AuthenticationError | openai.PermissionDeniedError):
        return "鉴权失败"
    if isinstance(exc, openai.RateLimitError):
        return "额度不足或限流"
    if isinstance(exc, openai.APIConnectionError):
        return "无法连接模型网关"
    return type(exc).__name__


class FallbackLLM:
    """The real model; after a gateway failure before any output, the demo for the rest of the run.

    Failures after output has started are re-raised: half an answer cannot be continued by another
    model. The switch is announced once with a ("notice", text) chunk on the next stream.
    """

    def __init__(self, primary, demo: MockLLM) -> None:
        self.primary, self.demo = primary, demo
        self._active = primary
        self._notice: str | None = None

    @property
    def model(self) -> str:
        return self._active.model

    @property
    def protocol(self) -> str:
        return self._active.protocol

    @property
    def last_usage(self) -> tuple[int, int]:
        return self._active.last_usage

    @property
    def tokens(self) -> int:
        return self.primary.tokens + self.demo.tokens

    def _switch(self, exc: Exception) -> None:
        self._active = self.demo
        self._notice = DEMO_NOTICE.format(reason=_reason(exc))

    async def stream(self, messages) -> AsyncIterator[tuple[str, str]]:
        if self._active is self.primary:
            started = False
            try:
                async for item in self.primary.stream(messages):
                    started = True
                    yield item
                return
            except FALLBACK_ERRORS as exc:
                if started:
                    raise
                self._switch(exc)
        if self._notice:
            yield "notice", self._notice
            self._notice = None
        async for item in self.demo.stream(messages):
            yield item

    async def complete(self, messages) -> str:
        if self._active is self.primary:
            try:
                return await self.primary.complete(messages)
            except FALLBACK_ERRORS as exc:
                self._switch(exc)
        return await self.demo.complete(messages)
