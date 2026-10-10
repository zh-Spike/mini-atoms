import pytest

from app.agents.parser import FileStreamParser, extract_markdown_files


def _run(text: str, size: int) -> FileStreamParser:
    p = FileStreamParser()
    for i in range(0, len(text), size):
        p.feed(text[i : i + size])
    p.close()
    return p


REPLY = (
    "开始写代码\n"
    '<file path="/App.js">\n'
    "export default function App() {\n  return <div>a < b</div>;\n}\n</file>\n"
    '<file path="components/List.js">\n```jsx\nexport const x = 1;\n```\n</file>\n'
    '<delete path="/old.js"/>\n完成。'
)


@pytest.mark.parametrize("size", [1, 3, 7, 1000])
def test_parses_files_regardless_of_chunking(size: int) -> None:
    p = _run(REPLY, size)
    assert set(p.files) == {"/App.js", "/components/List.js"}
    assert "a < b" in p.files["/App.js"]
    assert p.files["/components/List.js"] == "export const x = 1;\n"
    assert p.deleted == ["/old.js"]
    assert "开始写代码" in p.text and "完成。" in p.text
    assert "<file" not in p.text


def test_events_are_ordered() -> None:
    p = FileStreamParser()
    events = p.feed(REPLY) + p.close()
    kinds = [e.kind for e in events if e.kind != "file_delta"]
    assert kinds[:3] == ["text", "file_start", "file_end"]
    assert kinds.count("file_end") == 2


def test_markdown_fallback_finds_paths() -> None:
    text = (
        "### `/App.js`\n```jsx\nexport default function App() {}\n```\n"
        "```js\n// components/List.js\nexport const a = 1;\n```\n"
        "**styles.css**\n```css\nbody{}\n```\n"
        "```bash\nnpm i\n```"
    )
    files = extract_markdown_files(text)
    assert set(files) == {"/App.js", "/components/List.js", "/styles.css"}


def test_unclosed_file_is_flushed_on_close() -> None:
    p = _run('<file path="/App.js">\nexport default 1;\n', 4)
    assert p.files["/App.js"] == "export default 1;\n"
