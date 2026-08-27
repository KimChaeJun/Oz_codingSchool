from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pwdlib.exceptions import PwdlibError
from pydantic import BaseModel, ValidationError

from app.core.config import settings

TokenType = Literal["access", "refresh"]


class TokenPayload(BaseModel):
    user_id: int
    token_type: TokenType
    iat: datetime
    exp: datetime


class TokenValidationError(ValueError):
    """JWT가 없거나 유효하지 않을 때 사용하는 인증 예외입니다."""


password_hash = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hash.hash("dummy-password-for-timing-protection")


def hash_password(plain_password: str) -> str:
    return password_hash.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return password_hash.verify(plain_password, hashed_password)
    except (PwdlibError, ValueError):
        return False


def _create_token(user_id: int, token_type: TokenType, expires_delta: timedelta) -> str:
    now = datetime.now(UTC)
    payload = {
        "user_id": user_id,
        "token_type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )


def create_access_token(user_id: int) -> str:
    return _create_token(
        user_id,
        "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: int) -> str:
    return _create_token(
        user_id,
        "refresh",
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str, expected_type: TokenType) -> TokenPayload:
    try:
        decoded = jwt.decode(
            token,
            settings.JWT_SECRET_KEY.get_secret_value(),
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["user_id", "token_type", "iat", "exp"]},
        )
        payload = TokenPayload.model_validate(decoded)
    except (InvalidTokenError, ValidationError, ValueError, TypeError) as exc:
        raise TokenValidationError("유효하지 않은 인증 토큰입니다.") from exc

    if payload.token_type != expected_type:
        raise TokenValidationError("토큰 종류가 올바르지 않습니다.")
    return payload
