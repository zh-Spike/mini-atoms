"""Incremental parser for `<file path="...">...</file>` blocks in a streamed LLM reply."""

import re
from dataclasses import dataclass

OPEN_PREFIX = '<file path="'
CLOSE_TAG = "</file>"
OPEN_RE = re.compile(r'<file path="([^"]+)"\s*>')
DELETE_RE = re.compile(r'<delete path="([^"]+)"\s*/>')
FENCE_RE = re.compile(r"^\s*```[\w-]*\n(.*?)\n?```\s*$", re.S)


@dataclass
class Event:
    kind: str  # text | file_start | file_delta | file_end
    text: str = ""
    path: str = ""


MD_BLOCK_RE = re.compile(r"```([^\n]*)\n(.*?)```", re.S)
PATH_RE = re.compile(r"(/?(?:[\w-]+/)*[\w-]+\.(?:jsx?|css))\b")
FIRST_LINE_COMMENT_RE = re.compile(r"^\s*(?://|/\*)\s*(\S+\.(?:jsx?|css))")


def extract_markdown_files(text: str) -> dict[str, str]:
    """Fallback for replies that ignored the <file> format and used fenced code blocks.

    The path is taken from the fence info string, the line right before the fence, or a
    leading comment; an unnamed block that defines `App` is assumed to be /App.js.
    """
    files: dict[str, str] = {}
    for m in MD_BLOCK_RE.finditer(text):
        info, code = m.group(1), m.group(2)
        before = text[: m.start()].rstrip().rsplit("\n", 1)[-1]
        path = None
        for source in (info, before):
            found = PATH_RE.search(source)
            if found:
                path = found.group(1)
                break
        if path is None:
            first = FIRST_LINE_COMMENT_RE.match(code)
            if first:
                path = first.group(1)
            elif "export default function App" in code:
                path = "/App.js"
        if path:
            files[normalize_path(path)] = code.strip("\n") + "\n"
    return files


def strip_code_blocks(text: str) -> str:
    return MD_BLOCK_RE.sub("", text).strip()


def normalize_path(path: str) -> str:
    path = path.strip().replace("\\", "/")
    return path if path.startswith("/") else "/" + path


def clean_content(content: str) -> str:
    m = FENCE_RE.match(content)
    if m:
        content = m.group(1)
    return content.strip("\n") + "\n"


def _partial_suffix_len(buf: str, token: str) -> int:
    """Length of the longest suffix of buf that is a proper prefix of token."""
    for n in range(min(len(buf), len(token) - 1), 0, -1):
        if token.startswith(buf[-n:]):
            return n
    return 0


class FileStreamParser:
    def __init__(self) -> None:
        self._buf = ""
        self._path: str | None = None
        self._content: list[str] = []
        self.files: dict[str, str] = {}
        self.text_parts: list[str] = []

    @property
    def text(self) -> str:
        return "".join(self.text_parts)

    @property
    def deleted(self) -> list[str]:
        return [normalize_path(p) for p in DELETE_RE.findall(self.text)]

    def feed(self, chunk: str) -> list[Event]:
        self._buf += chunk
        events: list[Event] = []
        while True:
            if self._path is None:
                idx = self._buf.find(OPEN_PREFIX)
                if idx == -1:
                    keep = _partial_suffix_len(self._buf, OPEN_PREFIX)
                    self._emit_text(self._buf[: len(self._buf) - keep], events)
                    self._buf = self._buf[len(self._buf) - keep :]
                    return events
                m = OPEN_RE.match(self._buf, idx)
                if m is None:
                    if ">" in self._buf[idx:]:
                        # Malformed tag: treat as text and move on.
                        self._emit_text(self._buf[: idx + 1], events)
                        self._buf = self._buf[idx + 1 :]
                        continue
                    self._emit_text(self._buf[:idx], events)
                    self._buf = self._buf[idx:]
                    return events
                self._emit_text(self._buf[:idx], events)
                self._path = normalize_path(m.group(1))
                self._content = []
                self._buf = self._buf[m.end() :]
                events.append(Event("file_start", path=self._path))
            else:
                idx = self._buf.find(CLOSE_TAG)
                if idx == -1:
                    keep = _partial_suffix_len(self._buf, CLOSE_TAG)
                    self._emit_content(self._buf[: len(self._buf) - keep], events)
                    self._buf = self._buf[len(self._buf) - keep :]
                    return events
                self._emit_content(self._buf[:idx], events)
                self._buf = self._buf[idx + len(CLOSE_TAG) :]
                self._finish_file(events)

    def close(self) -> list[Event]:
        events: list[Event] = []
        if self._path is not None:
            self._emit_content(self._buf, events)
            self._finish_file(events)
        else:
            self._emit_text(self._buf, events)
        self._buf = ""
        return events

    def _emit_text(self, text: str, events: list[Event]) -> None:
        if text:
            self.text_parts.append(text)
            events.append(Event("text", text=text))

    def _emit_content(self, text: str, events: list[Event]) -> None:
        if text and self._path is not None:
            self._content.append(text)
            events.append(Event("file_delta", text=text, path=self._path))

    def _finish_file(self, events: list[Event]) -> None:
        assert self._path is not None
        content = clean_content("".join(self._content))
        self.files[self._path] = content
        events.append(Event("file_end", text=content, path=self._path))
        self._path = None
        self._content = []
