import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from backend.app.core.database import SessionLocal
from backend.app.core.dependencies import get_db
from backend.app.models.user import User

DEFAULT_ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
JWT_SECRET_KEY = os.getenv("APP_SECRET_KEY", "smart-schedule-admin-secret-key")
APP_ENV = os.getenv("APP_ENV", "development").lower()
JWT_ALGORITHM = "HS256"
JWT_TTL_HOURS = 8
security = HTTPBearer(auto_error=False)

if APP_ENV == "production":
    if JWT_SECRET_KEY == "smart-schedule-admin-secret-key":
        raise RuntimeError("APP_SECRET_KEY must be configured in production.")
    if DEFAULT_ADMIN_PASSWORD == "admin123":
        raise RuntimeError("ADMIN_PASSWORD must be configured in production.")


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        150000,
    )
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash or not password_hash.startswith("pbkdf2_sha256$"):
        return False

    try:
        _, salt, expected_hash = password_hash.split("$", 2)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        150000,
    )
    return hmac.compare_digest(digest.hex(), expected_hash)


def create_access_token(user: User) -> str:
    payload: dict[str, Any] = {
        "sub": str(user.id),
        "username": user.username,
        "is_admin": bool(user.is_admin),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_TTL_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или просроченный токен",
        ) from exc


def get_current_admin_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_payload = decode_access_token(credentials.credentials)
    user_id = token_payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен не содержит пользователя",
        )

    try:
        parsed_user_id = int(user_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен содержит некорректного пользователя",
        ) from exc

    user = db.query(User).filter(User.id == parsed_user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден или отключён",
        )

    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для администратора",
        )

    return user


def ensure_user_schema() -> None:
    # Schema changes are managed exclusively by Alembic migrations.
    return


def ensure_default_admin_user() -> None:
    ensure_user_schema()

    db = SessionLocal()
    try:
        user = (
            db.query(User)
            .filter(User.username == DEFAULT_ADMIN_USERNAME)
            .first()
        )

        if user is None:
            user = User(
                username=DEFAULT_ADMIN_USERNAME,
                password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
                full_name="Администратор",
                is_active=True,
                is_admin=True,
            )
            db.add(user)
            db.commit()
            return

        if user.is_admin is not True:
            user.is_admin = True
        if user.is_active is not True:
            user.is_active = True
        if not user.full_name:
            user.full_name = "Администратор"

        db.commit()
    finally:
        db.close()


async def require_admin_access(request: Request, call_next):
    open_paths = {
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/auth/login",
    }

    static_extensions = (".html", ".js", ".css", ".ico", ".png", ".jpg", ".svg")
    if (
        request.method == "OPTIONS"
        or request.url.path in open_paths
        or request.url.path == "/"
        or request.url.path.endswith(static_extensions)
    ):
        return await call_next(request)

    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Требуется авторизация"},
        )

    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Неверный или просроченный токен"},
        )

    if not payload.get("is_admin"):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "Доступ только для администратора"},
        )

    request.state.user = payload
    return await call_next(request)
