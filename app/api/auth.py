from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from app.auth import COOKIE_NAME, CurrentGuest, DbSession, redeem_invite, set_session_cookie
from app.config import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class InviteIn(BaseModel):
    code: str = Field(min_length=1, max_length=64)


def _me(guest) -> dict:
    return {
        "guest_id": guest.id,
        "invite_code": guest.invite_code,
        "generations_used": guest.generations_used,
        "generation_limit": get_settings().guest_generation_limit,
    }


@router.post("/invite")
def invite(body: InviteIn, request: Request, response: Response, db: DbSession) -> dict:
    guest = redeem_invite(db, body.code)
    set_session_cookie(response, guest.id, secure=request.url.scheme == "https")
    return _me(guest)


@router.get("/me")
def me(guest: CurrentGuest) -> dict:
    return _me(guest)


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}
