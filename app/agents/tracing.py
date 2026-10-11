"""Per-call LLM tracing: every model call in a run becomes one `llm_calls` row.

`TracedLLM` wraps any `LLM` (the real client or a test fake) and records the prompt, reasoning,
output, token usage, time to first token and outcome.

Writes go through one background thread, in submission order: the database can be a few hundred
milliseconds away, and a synchronous insert between two agents would both delay the next agent and
block the event loop for every other request.
"""

import asyncio
import logging
import time
from collections.abc import AsyncIterator, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.agents.llm import LLM, ChatMessages, ChunkKind
from app.db import SessionLocal
from app.models import LLMCall

log = logging.getLogger(__name__)

MAX_TEXT = 100_000

_writer = ThreadPoolExecutor(max_workers=1, thread_name_prefix="trace-writer")


def write_later(fn: Callable[[], None]) -> None:
    """Run a bookkeeping write on the trace writer thread; failures are logged, never raised."""

    def run() -> None:
        try:
            fn()
        except Exception:
            log.exception("trace write failed")

    _writer.submit(run)


def flush(timeout: float = 30) -> None:
    """Wait until every write submitted so far has finished."""
    _writer.submit(lambda: None).result(timeout)


def store(row) -> None:
    with SessionLocal() as db:
        db.add(row)
        db.commit()


def _clip(text: str) -> str:
    return text if len(text) <= MAX_TEXT else text[:MAX_TEXT] + "\n…（已截断）"


@dataclass
class CallSummary:
    agent: str
    step: str
    lane: int | None
    model: str
    prompt_tokens: int
    completion_tokens: int
    duration_ms: int
    status: str


@dataclass
class Tracer:
    run_id: str
    calls: list[CallSummary] = field(default_factory=list)

    def wrap(self, llm: LLM, agent: str, step: str | None = None, lane: int | None = None):
        return TracedLLM(llm, self, agent, step or agent, lane)

    @property
    def prompt_tokens(self) -> int:
        return sum(c.prompt_tokens for c in self.calls)

    @property
    def completion_tokens(self) -> int:
        return sum(c.completion_tokens for c in self.calls)

    def by_agent(self) -> list[dict]:
        """Per-agent totals in first-seen order, for the run's `done` stats."""
        out: dict[tuple[str, str], dict] = {}
        for c in self.calls:
            row = out.setdefault(
                (c.agent, c.model),
                {"agent": c.agent, "model": c.model, "tokens": 0, "duration_ms": 0, "calls": 0},
            )
            row["tokens"] += c.prompt_tokens + c.completion_tokens
            row["duration_ms"] += c.duration_ms
            row["calls"] += 1
        return list(out.values())

    def record(self, call: LLMCall) -> None:
        self.calls.append(
            CallSummary(
                call.agent,
                call.step,
                call.lane,
                call.model,
                call.prompt_tokens,
                call.completion_tokens,
                call.duration_ms,
                call.status,
            )
        )
        write_later(lambda: store(call))


class TracedLLM:
    def __init__(self, inner: LLM, tracer: Tracer, agent: str, step: str, lane: int | None):
        self.inner, self.tracer = inner, tracer
        self.agent, self.step, self.lane = agent, step, lane

    def at(self, step: str) -> "TracedLLM":
        """Same model and agent, recorded under another step name (retry, fix)."""
        return TracedLLM(self.inner, self.tracer, self.agent, step, self.lane)

    def _finish(
        self,
        messages: ChatMessages,
        started: float,
        started_at: datetime,
        first: float | None,
        thinking: list[str],
        output: list[str],
        status: str,
        error: str | None,
    ) -> None:
        prompt, completion = getattr(self.inner, "last_usage", (0, 0))
        self.tracer.record(
            LLMCall(
                run_id=self.tracer.run_id,
                agent=self.agent,
                step=self.step,
                lane=self.lane,
                model=getattr(self.inner, "model", "") or "",
                protocol=getattr(self.inner, "protocol", "") or "",
                messages=[{**m, "content": _clip(m["content"])} for m in messages],
                thinking=_clip("".join(thinking)),
                output=_clip("".join(output)),
                prompt_tokens=prompt,
                completion_tokens=completion,
                ttft_ms=int((first - started) * 1000) if first is not None else None,
                duration_ms=int((time.monotonic() - started) * 1000),
                status=status,
                error=error,
                started_at=started_at,
            )
        )

    async def stream(self, messages: ChatMessages) -> AsyncIterator[tuple[ChunkKind, str]]:
        started, started_at = time.monotonic(), datetime.now(UTC)
        first: float | None = None
        thinking: list[str] = []
        output: list[str] = []
        status, error = "ok", None
        try:
            async for kind, chunk in self.inner.stream(messages):
                if first is None:
                    first = time.monotonic()
                (thinking if kind == "think" else output).append(chunk)
                yield kind, chunk
        except BaseException as exc:
            status, error = ("aborted", None) if _is_cancel(exc) else ("error", str(exc))
            raise
        finally:
            self._finish(messages, started, started_at, first, thinking, output, status, error)

    async def complete(self, messages: ChatMessages) -> str:
        started, started_at = time.monotonic(), datetime.now(UTC)
        text, status, error = "", "ok", None
        try:
            text = await self.inner.complete(messages)
            return text
        except BaseException as exc:
            status, error = ("aborted", None) if _is_cancel(exc) else ("error", str(exc))
            raise
        finally:
            first = time.monotonic() if status == "ok" else None
            self._finish(messages, started, started_at, first, [], [text], status, error)


def _is_cancel(exc: BaseException) -> bool:
    return isinstance(exc, asyncio.CancelledError | GeneratorExit)
