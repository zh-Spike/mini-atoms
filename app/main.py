from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import admin, auth, projects, share, status, usage
from app.auth import sync_invite_codes
from app.config import get_settings
from app.db import SessionLocal, init_db

STATIC_DIR = Path(__file__).resolve().parent / "static"

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with SessionLocal() as db:
        sync_invite_codes(db)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(share.router)
app.include_router(usage.router)
app.include_router(admin.router)
app.include_router(status.router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


if (STATIC_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def spa(path: str):
    if path.startswith("api/"):
        raise HTTPException(status_code=404)
    file = (STATIC_DIR / path).resolve()
    if path and file.is_file() and file.is_relative_to(STATIC_DIR):
        return FileResponse(file)
    index = STATIC_DIR / "index.html"
    if index.is_file():
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
    return JSONResponse({"detail": "frontend not built; run `npm run build` in web/"}, 404)
