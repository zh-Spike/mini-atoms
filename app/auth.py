import hashlib
import hmac
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response
from itsdangerous import BadSignature, URLSafeSerializer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import InviteCode, User

COOKIE_NAME = "ma_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30

_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1


def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(get_settings().secret_key, salt="user-session")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, digest = stored.split("$")
        actual = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p)
        )
    except ValueError:
        return False
    return hmac.compare_digest(actual.hex(), digest)


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


def register_user(db: Session, invite_code: str, username: str, password: str) -> User:
    invite = db.get(InviteCode, invite_code.strip())
    if invite is None or not invite.enabled:
        raise HTTPException(status_code=400, detail="邀请码无效")
    if invite.used_count >= invite.max_uses:
        raise HTTPException(status_code=400, detail="邀请码已达使用上限")
    username = username.strip().lower()
    if db.query(User).filter(User.username == username).first() is not None:
        raise HTTPException(status_code=409, detail="用户名已被占用")
    invite.used_count += 1
    user = User(username=username, password_hash=hash_password(password), invite_code=invite.code)
    db.add(user)
    db.commit()
    return user


def authenticate(db: Session, username: str, password: str) -> User:
    user = db.query(User).filter(User.username == username.strip().lower()).first()
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return user


def set_session_cookie(response: Response, user_id: str, secure: bool) -> None:
    response.set_cookie(
        COOKIE_NAME,
        _serializer().dumps(user_id),
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=secure,
    )


def current_user(request: Request, db: Annotated[Session, Depends(get_db)]) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="请先登录")
    try:
        user_id = _serializer().loads(token)
    except BadSignature as exc:
        raise HTTPException(status_code=401, detail="会话无效") from exc
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="会话无效")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
DbSession = Annotated[Session, Depends(get_db)]


def is_admin(user: User) -> bool:
    admins = {u.strip().lower() for u in get_settings().admin_usernames.split(",") if u.strip()}
    return user.username in admins


def require_admin(user: CurrentUser) -> User:
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


AdminUser = Annotated[User, Depends(require_admin)]
