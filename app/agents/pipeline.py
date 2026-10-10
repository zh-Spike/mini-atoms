"""Multi-agent orchestration: Mike routes, Emma writes the PRD, Bob designs, Alex codes, QA checks.

`run_pipeline` is an async generator of JSON-serializable events that the API streams as NDJSON.
"""

import json
import logging
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.agents import prompts
from app.agents.llm import LLM, ChatMessages
from app.agents.parser import (
    DELETE_RE,
    FileStreamParser,
    extract_markdown_files,
    strip_code_blocks,
)
from app.agents.qa import check_project
from app.models import Message, Project, Version
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
    db: Session, project: Project, files: dict[str, str], source: str, summary: str
) -> Version:
    number = (
        db.query(func.max(Version.number)).filter(Version.project_id == project.id).scalar() or 0
    ) + 1
    version = Version(
        project_id=project.id, number=number, files=files, source=source, summary=summary
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


async def run_pipeline(
    db: Session, project: Project, user_text: str, llm: LLM
) -> AsyncIterator[Event]:
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

        alex = _CodeAgent(llm, alex_messages)
        async for e in alex.run():
            yield e
        files = {**base_files, **alex.files}
        for path in alex.deleted:
            files.pop(path, None)
        alex_msg = _save_message(
            db,
            project,
            "agent",
            _alex_message(alex.summary, sorted(alex.files), alex.deleted),
            agent="alex",
        )
        yield _ev("agent_end", agent="alex", message=message_out(alex_msg))

        if not alex.files and not alex.deleted:
            yield _ev("done")
            return

        yield _ev("agent_start", agent="qa")
        issues = check_project(files)
        summary = alex.summary
        if issues:
            report = "发现以下问题，已交给 Alex 修复：\n" + "\n".join(f"- {i}" for i in issues)
            yield _ev("delta", agent="qa", text=report)
            msg = _save_message(db, project, "agent", report, agent="qa")
            yield _ev("agent_end", agent="qa", message=message_out(msg), ok=False, issues=issues)

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
            msg = _save_message(
                db,
                project,
                "agent",
                _alex_message(fixer.summary, sorted(fixer.files), fixer.deleted),
                agent="alex",
            )
            yield _ev("agent_end", agent="alex", message=message_out(msg))
            alex_msg = msg
            yield _ev("agent_start", agent="qa")
            issues = check_project(files)

        if issues:
            report = "仍有问题未解决，预览可能报错：\n" + "\n".join(f"- {i}" for i in issues)
        else:
            report = f"静态检查通过：{len(files)} 个文件，入口、依赖和相对引用均正常。"
        yield _ev("delta", agent="qa", text=report)
        msg = _save_message(db, project, "agent", report, agent="qa")
        yield _ev("agent_end", agent="qa", message=message_out(msg), ok=not issues, issues=issues)

        version = create_version(db, project, files, "ai", summary[:500])
        alex_msg.version_id = version.id
        db.commit()
        yield _ev("version", version=version_out(version), message_id=alex_msg.id)
        yield _ev("done")
    except Exception as exc:  # surface any failure to the client instead of a broken stream
        log.exception("pipeline failed for project %s", project.id)
        db.rollback()
        msg = _save_message(db, project, "system", f"运行出错：{exc}")
        yield _ev("error", message=str(exc), saved=message_out(msg))
