from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db.databases import async_get_db
from app.core.security import create_access_token, get_current_user, get_refresh_token
from app.schemas.user import LoginRequest, LoginResponse
from app.services.user import login_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

COOKIE_SECURE = settings.ENVIRONMENT == "production"


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="로그인",
)
async def login(
    body: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> LoginResponse:
    token_response = await login_user(db, body.email, body.password)

    response.set_cookie(
        key="refresh_token",
        value=token_response.refresh_token,
        max_age=7 * 24 * 60 * 60,
        path="/",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
    )

    return LoginResponse(
        access_token=token_response.access_token,
        token_type=token_response.token_type,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="로그아웃",
)
async def logout(
    response: Response,
    _: Annotated[int, Depends(get_current_user)],
) -> None:
    response.delete_cookie(
        key="refresh_token",
        path="/",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
    )


@router.post(
    "/refresh",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Access Token 재발급",
)
async def refresh(
    payload: Annotated[dict, Depends(get_refresh_token)],
) -> LoginResponse:
    user_id = payload["sub"]

    new_access_token = create_access_token(data={"sub": user_id})

    return LoginResponse(
        access_token=new_access_token,
        token_type="bearer",
    )
