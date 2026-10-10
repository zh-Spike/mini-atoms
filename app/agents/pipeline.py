"""Multi-agent orchestration: Mike routes, Emma writes the PRD, Bob designs, Alex codes, QA checks.

`run_pipeline` is an async generator of JSON-serializable events that the API streams as NDJSON.
In race mode several Alex lanes code the same PRD in parallel and each lane becomes a candidate
version; lane events carry a `lane` index.
"""

import asyncio
import json
import logging
import re
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.agents import prompts
from app.agents.llm import LLM, ChatMessages, RaceLane
from app.agents.parser import (
    DELETE_RE,
    FileStreamParser,
    extract_markdown_files,
    strip_code_blocks,
)
from app.agents.qa import check_project
from app.config import get_settings
from app.models import Message, Project, User, Version
from app.serializers import message_out, version_out

log = logging.getLogger(__name__)

Event = dict


def _ev(type_: str, **kw) -> Event:
    return {"type": type_, **kw}


def _save_message(db: Session, project: Project, role: str, content: str, **kw) -> Message:
    msg = Message(project_id=project.id, role=role, content=content, **kw)
    db.add(msg)
    db.commit()
    return msg


def latest_version(db: Session, project: Project) -> Version | None:
    return (
        db.query(Version)
        .filter(Version.project_id == project.id)
        .order_by(Version.number.desc())
        .first()
    )


def create_version(
    db: Session,
    project: Project,
    files: dict[str, str],
    source: str,
    summary: str,
    label: str | None = None,
) -> Version:
    number = (
        db.query(func.max(Version.number)).filter(Version.project_id == project.id).scalar() or 0
    ) + 1
    version = Version(
        project_id=project.id,
        number=number,
        files=files,
        source=source,
        summary=summary,
        label=label,
    )
    db.add(version)
    project.updated_at = datetime.now(UTC)
    db.commit()
    return version


def _latest_agent_text(db: Session, project: Project, agent: str) -> str:
    msg = (
        db.query(Message)
        .filter(Message.project_id == project.id, Message.agent == agent)
        .order_by(Message.created_at.desc())
        .first()
    )
    return msg.content if msg else ""


class _TextAgent:
    """Streams a plain-text agent reply and stores the final text in `.text`."""

    def __init__(self, llm: LLM, agent: str, messages: ChatMessages) -> None:
        self.llm, self.agent, self.messages = llm, agent, messages
        self.text = ""

    async def run(self) -> AsyncIterator[Event]:
        yield _ev("agent_start", agent=self.agent)
        parts: list[str] = []
        async for kind, chunk in self.llm.stream(self.messages):
            if kind == "think":
                yield _ev("thinking", agent=self.agent, text=chunk)
                continue
            parts.append(chunk)
            yield _ev("delta", agent=self.agent, text=chunk)
        self.text = "".join(parts).strip()


class _CodeAgent:
    """Streams Alex's reply, parsing `<file>` blocks into `.files` as they arrive.

    Falls back to Markdown code blocks if the model ignores the format, and retries once
    with a correction if no file could be recovered at all.
    """

    def __init__(self, llm: LLM, messages: ChatMessages) -> None:
        self.llm = llm
        self.messages = [*messages[:-1], _with_reminder(messages[-1])]
        self.parser = FileStreamParser()
        self.files: dict[str, str] = {}
        self.deleted: list[str] = []
        self.summary = ""

    async def run(self) -> AsyncIterator[Event]:
        yield _ev("agent_start", agent="alex")
        async for e in self._attempt(self.messages):
            yield e
        if not self.files and not self.deleted:
            log.warning("alex returned no parsable files; retrying with format correction")
            yield _ev("delta", agent="alex", text="\n\n（输出格式不符合要求，正在重新输出…）\n\n")
            retry = [
                *self.messages,
                {"role": "assistant", "content": self.parser.text[:4000]},
                {"role": "user", "content": prompts.FORMAT_RETRY},
            ]
            self.parser = FileStreamParser()
            async for e in self._attempt(retry):
                yield e

    async def _attempt(self, messages: ChatMessages) -> AsyncIterator[Event]:
        async for kind, chunk in self.llm.stream(messages):
            if kind == "think":
                yield _ev("thinking", agent="alex", text=chunk)
                continue
            for e in self.parser.feed(chunk):
                yield self._convert(e)
        for e in self.parser.close():
            yield self._convert(e)

        text = DELETE_RE.sub("", self.parser.text)
        self.files, self.deleted = dict(self.parser.files), self.parser.deleted
        if not self.files:
            self.files = extract_markdown_files(text)
            for path, content in self.files.items():
                yield _ev("file_start", agent="alex", path=path, text="")
                yield _ev("file_end", agent="alex", path=path, content=content)
            text = strip_code_blocks(text)
        self.summary = text.strip()

    @staticmethod
    def _convert(e) -> Event:
        if e.kind == "text":
            return _ev("delta", agent="alex", text=e.text)
        if e.kind == "file_end":
            return _ev("file_end", agent="alex", path=e.path, content=e.text)
        return _ev(e.kind, agent="alex", path=e.path, text=e.text)


def _with_reminder(message: dict[str, str]) -> dict[str, str]:
    return {**message, "content": message["content"] + prompts.FORMAT_REMINDER}


def _parse_route(raw: str) -> tuple[str, str]:
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        data = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        data = {}
    mode = data.get("mode") if data.get("mode") in ("edit", "rebuild") else "edit"
    reply = str(data.get("reply") or "收到，我让 Alex 直接在现有应用上修改。")
    return mode, reply


def _alex_message(summary: str, changed: list[str], deleted: list[str]) -> str:
    lines = [summary or "代码已更新。"]
    if changed:
        lines.append("\n变更文件：" + "、".join(f"`{p}`" for p in changed))
    if deleted:
        lines.append("删除文件：" + "、".join(f"`{p}`" for p in deleted))
    return "\n".join(lines)


@dataclass
class _BuildResult:
    files: dict[str, str] = field(default_factory=dict)
    summary: str = ""
    issues: list[str] = field(default_factory=list)
    changed: bool = False
    alex_msg: Message | None = None


async def _code_and_check(
    db: Session,
    project: Project,
    llm: LLM,
    alex_messages: ChatMessages,
    base_files: dict[str, str],
    result: _BuildResult,
    persist: bool = True,
) -> AsyncIterator[Event]:
    """Alex codes, QA checks, Alex fixes once if needed. Race lanes run with `persist=False`."""

    def end(agent: str, text: str, **kw) -> Event:
        if not persist:
            return _ev("agent_end", agent=agent, **kw)
        msg = _save_message(db, project, "agent", text, agent=agent)
        if agent == "alex":
            result.alex_msg = msg
        return _ev("agent_end", agent=agent, message=message_out(msg), **kw)

    alex = _CodeAgent(llm, alex_messages)
    async for e in alex.run():
        yield e
    files = {**base_files, **alex.files}
    for path in alex.deleted:
        files.pop(path, None)
    result.summary = alex.summary
    yield end("alex", _alex_message(alex.summary, sorted(alex.files), alex.deleted))
    if not alex.files and not alex.deleted:
        return
    result.changed = True

    yield _ev("agent_start", agent="qa")
    issues = check_project(files)
    if issues:
        report = "发现以下问题，已交给 Alex 修复：\n" + "\n".join(f"- {i}" for i in issues)
        yield _ev("delta", agent="qa", text=report)
        yield end("qa", report, ok=False, issues=issues)

        fixer = _CodeAgent(
            llm,
            [
                {"role": "system", "content": prompts.ALEX_FIX},
                {
                    "role": "user",
                    "content": f"当前文件：\n{prompts.format_files(files)}\n\n问题列表：\n"
                    + "\n".join(f"- {i}" for i in issues),
                },
            ],
        )
        async for e in fixer.run():
            yield e
        files.update(fixer.files)
        for path in fixer.deleted:
            files.pop(path, None)
        yield end("alex", _alex_message(fixer.summary, sorted(fixer.files), fixer.deleted))
        yield _ev("agent_start", agent="qa")
        issues = check_project(files)

    if issues:
        report = "仍有问题未解决，预览可能报错：\n" + "\n".join(f"- {i}" for i in issues)
    else:
        report = f"静态检查通过：{len(files)} 个文件，入口、依赖和相对引用均正常。"
    yield _ev("delta", agent="qa", text=report)
    yield end("qa", report, ok=not issues, issues=issues)
    result.files, result.issues = files, issues


def _lane_name(i: int) -> str:
    return f"方案 {chr(ord('A') + i)}"


async def _race(
    db: Session, project: Project, lanes: list[RaceLane], alex_messages: ChatMessages
) -> AsyncIterator[Event]:
    yield _ev("race_start", lanes=[lane.label for lane in lanes])
    queue: asyncio.Queue[Event | None] = asyncio.Queue()
    results = [_BuildResult() for _ in lanes]

    async def pump(i: int, lane: RaceLane) -> None:
        last = alex_messages[-1]
        messages = [*alex_messages[:-1], {**last, "content": last["content"] + lane.style}]
        try:
            async for e in _code_and_check(
                db, project, lane.llm, messages, {}, results[i], persist=False
            ):
                await queue.put({**e, "lane": i})
            await queue.put(_ev("lane_finished", lane=i, ok=not results[i].issues))
        except Exception as exc:
            log.exception("race lane %s failed for project %s", i, project.id)
            await queue.put(_ev("lane_error", lane=i, message=str(exc)))
        finally:
            await queue.put(None)

    tasks = [asyncio.create_task(pump(i, lane)) for i, lane in enumerate(lanes)]
    try:
        running = len(tasks)
        while running:
            e = await queue.get()
            if e is None:
                running -= 1
            else:
                yield e
    finally:
        for t in tasks:
            t.cancel()

    candidates: list[str] = []
    for i, (lane, r) in enumerate(zip(lanes, results, strict=True)):
        if not r.changed:
            continue
        version = create_version(db, project, r.files, "race", r.summary[:500], label=lane.label)
        qa = "静态检查通过" if not r.issues else f"静态检查仍有 {len(r.issues)} 个问题"
        msg = _save_message(
            db,
            project,
            "agent",
            f"**{_lane_name(i)} · {lane.label}**\n\n{r.summary or '代码已生成。'}\n\n"
            f"{len(r.files)} 个文件，{qa}。",
            agent="alex",
            version_id=version.id,
        )
        yield _ev("lane_done", lane=i, version=version_out(version), message=message_out(msg))
        candidates.append(version.id)
    if not candidates:
        raise RuntimeError("所有方案都没有产出代码")
    yield _ev("race_done", version_ids=candidates)


def _charge_extra_generations(db: Session, project: Project, extra: int) -> bool:
    """A race costs one generation per lane; the first was charged by the API. False if short."""
    user = db.get(User, project.user_id)
    if user is None or user.generations_used + extra > get_settings().user_generation_limit:
        return False
    user.generations_used += extra
    db.commit()
    return True


async def run_pipeline(
    db: Session,
    project: Project,
    user_text: str,
    llm: LLM,
    race_lanes: list[RaceLane] | None = None,
) -> AsyncIterator[Event]:
    started = time.monotonic()
    used_llms: list[object] = [llm]

    def done() -> Event:
        tokens = sum(getattr(m, "tokens", 0) for m in used_llms)
        duration_ms = int((time.monotonic() - started) * 1000)
        return _ev("done", stats={"duration_ms": duration_ms, "tokens": tokens})

    user_msg = _save_message(db, project, "user", user_text)
    yield _ev("user_message", message=message_out(user_msg))

    try:
        current = latest_version(db, project)
        base_files: dict[str, str] = dict(current.files) if current else {}
        mode = "build"

        if current is not None:
            yield _ev("agent_start", agent="mike")
            raw = await llm.complete(
                [
                    {"role": "system", "content": prompts.MIKE_ROUTER},
                    {
                        "role": "user",
                        "content": f"当前应用文件：{', '.join(sorted(base_files))}\n"
                        f"用户消息：{user_text}",
                    },
                ]
            )
            mode, reply = _parse_route(raw)
            yield _ev("delta", agent="mike", text=reply)
            msg = _save_message(db, project, "agent", reply, agent="mike")
            yield _ev("agent_end", agent="mike", message=message_out(msg))

        race = bool(race_lanes) and len(race_lanes) > 1 and mode in ("build", "rebuild")
        if race:
            assert race_lanes is not None
            if not _charge_extra_generations(db, project, len(race_lanes) - 1):
                race = False
                note = f"生成额度不足以进行 Race（需要 {len(race_lanes)} 次），本次按单方案生成。"
                yield _ev("notice", text=note)

        if mode in ("build", "rebuild"):
            base_files = {}
            emma = _TextAgent(
                llm,
                "emma",
                [
                    {"role": "system", "content": prompts.EMMA_PRD},
                    {"role": "user", "content": user_text},
                ],
            )
            async for e in emma.run():
                yield e
            msg = _save_message(db, project, "agent", emma.text, agent="emma")
            yield _ev("agent_end", agent="emma", message=message_out(msg))

            bob = _TextAgent(
                llm,
                "bob",
                [
                    {"role": "system", "content": prompts.BOB_DESIGN},
                    {"role": "user", "content": f"用户需求：{user_text}\n\nPRD：\n{emma.text}"},
                ],
            )
            async for e in bob.run():
                yield e
            msg = _save_message(db, project, "agent", bob.text, agent="bob")
            yield _ev("agent_end", agent="bob", message=message_out(msg))

            alex_messages: ChatMessages = [
                {"role": "system", "content": prompts.ALEX_BUILD},
                {
                    "role": "user",
                    "content": f"用户需求：{user_text}\n\nPRD：\n{emma.text}\n\n"
                    f"架构设计：\n{bob.text}",
                },
            ]
        else:
            prd = _latest_agent_text(db, project, "emma")
            alex_messages = [
                {"role": "system", "content": prompts.ALEX_EDIT},
                {
                    "role": "user",
                    "content": f"产品 PRD：\n{prd}\n\n"
                    f"当前文件：\n{prompts.format_files(base_files)}\n\n"
                    f"用户的修改要求：{user_text}",
                },
            ]

        if race:
            assert race_lanes is not None
            used_llms.extend(lane.llm for lane in race_lanes)
            async for e in _race(db, project, race_lanes, alex_messages):
                yield e
            yield done()
            return

        result = _BuildResult()
        async for e in _code_and_check(db, project, llm, alex_messages, base_files, result):
            yield e
        if not result.changed:
            yield done()
            return

        version = create_version(db, project, result.files, "ai", result.summary[:500])
        assert result.alex_msg is not None
        result.alex_msg.version_id = version.id
        db.commit()
        yield _ev("version", version=version_out(version), message_id=result.alex_msg.id)
        yield done()
    except Exception as exc:  # surface any failure to the client instead of a broken stream
        log.exception("pipeline failed for project %s", project.id)
        db.rollback()
        msg = _save_message(db, project, "system", f"运行出错：{exc}")
        yield _ev("error", message=str(exc), saved=message_out(msg))
