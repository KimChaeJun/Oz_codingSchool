from datetime import datetime, timedelta, UTC
from typing import Any, Annotated

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db.databases import async_get_db
from app.repositories.user import get_user_by_id

SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "token_type": ACCESS_TOKEN_TYPE})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "token_type": REFRESH_TOKEN_TYPE})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def verify_access_token(token: str) -> dict[str, Any]:
    payload = decode_token(token)
    if payload is None:
        raise ValueError("Invalid token")
    if not payload.get("sub"):
        raise ValueError("user_id not found in token")
    if payload.get("token_type") != ACCESS_TOKEN_TYPE:
        raise ValueError("Invalid token type")
    return payload


def verify_refresh_token(token: str) -> dict[str, Any]:
    payload = decode_token(token)
    if payload is None:
        raise ValueError("Invalid token")
    if not payload.get("sub"):
        raise ValueError("user_id not found in token")
    if payload.get("token_type") != REFRESH_TOKEN_TYPE:
        raise ValueError("Invalid token type")
    return payload


security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> int:
    try:
        payload = verify_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다.",
        )

    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다.",
        )

    return user_id


async def get_refresh_token(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> dict[str, Any]:
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh Token이 없거나 유효하지 않습니다.",
        )

    try:
        payload = verify_refresh_token(refresh_token)
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh Token이 없거나 유효하지 않습니다.",
        )

    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh Token이 없거나 유효하지 않습니다.",
        )

    return payload
