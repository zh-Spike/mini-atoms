from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from app.auth import (
    COOKIE_NAME,
    CurrentUser,
    DbSession,
    authenticate,
    register_user,
    set_session_cookie,
)
from app.config import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)


class RegisterIn(BaseModel):
    invite_code: str = Field(min_length=1, max_length=64)
    username: str = Field(min_length=3, max_length=32, pattern=r"^\s*[A-Za-z0-9_]+\s*$")
    password: str = Field(min_length=6, max_length=128)


def _me(user) -> dict:
    return {
        "user_id": user.id,
        "username": user.username,
        "generations_used": user.generations_used,
        "generation_limit": get_settings().user_generation_limit,
    }


@router.post("/register")
def register(body: RegisterIn, request: Request, response: Response, db: DbSession) -> dict:
    user = register_user(db, body.invite_code, body.username, body.password)
    set_session_cookie(response, user.id, secure=request.url.scheme == "https")
    return _me(user)


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, db: DbSession) -> dict:
    user = authenticate(db, body.username, body.password)
    set_session_cookie(response, user.id, secure=request.url.scheme == "https")
    return _me(user)


@router.get("/me")
def me(user: CurrentUser) -> dict:
    return _me(user)


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}
