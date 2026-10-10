# mini-atoms

A mini [Atoms](https://atoms.dev/)-style demo: describe an app in natural language, let an AI agent generate the code, and preview the result live in the browser.

> Work in progress.

## Stack

- **Backend**: FastAPI, Jinja2 templates, HTMX
- **LLM**: any OpenAI-compatible API (DeepSeek, Qwen, OpenRouter, ...)
- **Database**: SQLite locally, Postgres (Neon) in production
- **Deploy**: Render (`render.yaml`)

## Local development

```bash
uv sync
cp .env.example .env   # then fill in LLM_API_KEY
uv run uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000.

## Checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```
