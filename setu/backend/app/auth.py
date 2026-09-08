from datetime import datetime, timedelta, timezone
from threading import Lock
import time

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import JWT_EXPIRE_MINUTES, JWT_SECRET
from .db import get_db
from .models import User

bearer = HTTPBearer(auto_error=False)
USER_CACHE_TTL_SECONDS = 60
_user_cache: dict[int, tuple[float, User]] = {}
_user_cache_lock = Lock()


def cache_user(user: User) -> User:
    snapshot = User(id=user.id, email=user.email, password_hash="", role=user.role, full_name=user.full_name)
    with _user_cache_lock:
        _user_cache[user.id] = (time.monotonic(), snapshot)
    return snapshot


def invalidate_cached_user(user_id: int) -> None:
    with _user_cache_lock:
        _user_cache.pop(user_id, None)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=10)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired or token invalid")
    user_id = int(payload["sub"])
    with _user_cache_lock:
        cached = _user_cache.get(user_id)
        if cached is not None and time.monotonic() - cached[0] < USER_CACHE_TTL_SECONDS:
            return cached[1]
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
    return cache_user(user)


def require_role(*roles: str):
    def guard(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"This action needs role {' or '.join(roles)}, you are {user.role}")
        return user

    return guard
