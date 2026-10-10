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
- Runtime config is managed in the GitHub `production` environment and written to `/opt/mini-atoms/.env` (mode 600) on every deploy. A missing value fails the deploy before anything restarts.
  - secrets: `DATABASE_URL`, `LLM_API_KEY`
  - variables: `LLM_BASE_URL`, `LLM_MODEL`
  - To change one: update it under *Settings → Environments → production*, then re-run *Deploy*. To add a new key, also add it to the *Upload runtime config* step.
- Deploy access: repo variable `DEPLOY_HOST`; repo secrets `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_KNOWN_HOSTS`.
- Roll back: *Actions → Deploy → Run workflow* with an older commit SHA.
