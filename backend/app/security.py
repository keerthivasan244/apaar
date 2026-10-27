"""Password hashing, JWT handling and role-based dependencies."""
import base64
import hashlib
import hmac
import os
import time
from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import User

PBKDF2_ITERATIONS = 200_000
ROLES = ("institution_admin", "aicte_officer", "student", "verifier")

_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS, base64.b64encode(salt).decode(), base64.b64encode(digest).decode()
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        _algo, iterations, salt_b64, digest_b64 = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt_b64), int(iterations))
        return hmac.compare_digest(digest, base64.b64decode(digest_b64))
    except (ValueError, TypeError):
        return False


def create_token(user: User) -> str:
    settings = get_settings()
    now = int(time.time())
    claims = {"sub": str(user.id), "role": user.role, "iat": now, "exp": now + settings.jwt_expiry_hours * 3600}
    return jwt.encode(claims, settings.jwt_secret, algorithm="HS256")


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer), db: Session = Depends(get_db)
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        claims = jwt.decode(creds.credentials, get_settings().jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = db.get(User, int(claims["sub"]))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
    return user


def require_roles(*roles: str) -> Callable[..., User]:
    """Dependency factory: the current user must hold one of `roles`."""

    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot access this resource")
        return user

    return _dep


OFFICER = "aicte_officer"
INSTITUTION = "institution_admin"
STUDENT = "student"
VERIFIER = "verifier"


def scoped_college_id(user: User, requested: int | None) -> int | None:
    """Institution admins are always scoped to their own college."""
    if user.role == INSTITUTION:
        return user.college_id
    return requested


def assert_college_access(user: User, college_id: int) -> None:
    if user.role == OFFICER:
        return
    if user.role == INSTITUTION and user.college_id == college_id:
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot access this institution")
