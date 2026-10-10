from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response
from itsdangerous import BadSignature, URLSafeSerializer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Guest, InviteCode

COOKIE_NAME = "ma_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30


def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(get_settings().secret_key, salt="guest-session")


def parse_invite_codes(raw: str) -> dict[str, int]:
    codes: dict[str, int] = {}
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        code, _, uses = item.partition(":")
        code = code.strip()
        if code:
            codes[code] = int(uses) if uses.strip().isdigit() else 10
    return codes


def sync_invite_codes(db: Session) -> None:
    """Make the DB match INVITE_CODES: upsert listed codes, disable the rest."""
    wanted = parse_invite_codes(get_settings().invite_codes)
    for row in db.query(InviteCode).all():
        if row.code in wanted:
            row.max_uses = wanted.pop(row.code)
            row.enabled = True
        else:
            row.enabled = False
    for code, max_uses in wanted.items():
        db.add(InviteCode(code=code, max_uses=max_uses))
    db.commit()


def redeem_invite(db: Session, code: str) -> Guest:
    invite = db.get(InviteCode, code.strip())
    if invite is None or not invite.enabled:
        raise HTTPException(status_code=400, detail="邀请码无效")
    if invite.used_count >= invite.max_uses:
        raise HTTPException(status_code=400, detail="邀请码已达使用上限")
    invite.used_count += 1
    guest = Guest(invite_code=invite.code)
    db.add(guest)
    db.commit()
    return guest


def set_session_cookie(response: Response, guest_id: str, secure: bool) -> None:
    response.set_cookie(
        COOKIE_NAME,
        _serializer().dumps(guest_id),
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=secure,
    )


def current_guest(request: Request, db: Annotated[Session, Depends(get_db)]) -> Guest:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="需要邀请码")
    try:
        guest_id = _serializer().loads(token)
    except BadSignature as exc:
        raise HTTPException(status_code=401, detail="会话无效") from exc
    guest = db.get(Guest, guest_id)
    if guest is None:
        raise HTTPException(status_code=401, detail="会话无效")
    invite = db.get(InviteCode, guest.invite_code)
    if invite is None or not invite.enabled:
        raise HTTPException(status_code=401, detail="邀请码已失效")
    return guest


CurrentGuest = Annotated[Guest, Depends(current_guest)]
DbSession = Annotated[Session, Depends(get_db)]
