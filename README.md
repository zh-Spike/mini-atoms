# mini-atoms

A mini [Atoms](https://atoms.dev/)-style demo: describe an app in natural language, let an AI agent generate the code, and preview the result live in the browser.

> Work in progress.

## Stack

- **Backend**: FastAPI, Jinja2 templates, HTMX
- **LLM**: any OpenAI-compatible API (DeepSeek, Qwen, OpenRouter, ...)
- **Database**: SQLite locally, Postgres (Neon) in production
- **Deploy**: Docker on a Tencent Cloud Lighthouse server (Hong Kong), via GitHub Actions

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

## Deployment

```
feature branch -> PR -> CI (lint, tests, docker build) -> squash merge to main
  -> CI on main -> Deploy workflow: build & push ghcr.io image -> SSH to server
  -> docker compose pull && up -d -> /healthz check
```

- `Dockerfile` builds the app image; `docker-compose.yml` runs it on the server (port 80, auto-restart).
- `.github/workflows/deploy.yml` runs only after CI succeeds on `main`, or manually via *Run workflow*.
- Runtime secrets (`DATABASE_URL`, `LLM_*`) live in `/opt/mini-atoms/.env` on the server, never in the repo.
- GitHub Secrets: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_KNOWN_HOSTS`.
