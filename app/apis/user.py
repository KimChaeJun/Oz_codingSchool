from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.user import (
    UserCreateRequest, UserResponse, UserProfileResponse, UserUpdateRequest,
    UserUpdateResponse, PasswordChangeRequest, RoleChangeRequest, RoleChangeResponse
)
from app.services.user import (
    register_user, get_profile, update_profile, change_password, delete_account,
    list_users, change_user_role
)


router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="회원가입",
)
async def register(
    body: UserCreateRequest,
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> User:
    return await register_user(db, body)


@router.get(
    "",
    response_model=list[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="회원 목록 조회",
)
async def get_users_list(
    current_user_id: Annotated[int, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    search: str | None = None,
    department: str | None = None,
) -> list[User]:
    current_user = await get_profile(db, current_user_id)
    return await list_users(db, current_user, search, department)


@router.get(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="마이페이지 조회",
)
async def get_my_profile(
    current_user_id: Annotated[int, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> User:
    return await get_profile(db, current_user_id)


@router.patch(
    "/me",
    response_model=UserUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="회원 정보 수정",
)
async def update_my_profile(
    body: UserUpdateRequest,
    current_user_id: Annotated[int, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> User:
    user = await get_profile(db, current_user_id)
    return await update_profile(db, user, body)


@router.patch(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="비밀번호 변경",
)
async def change_my_password(
    body: PasswordChangeRequest,
    current_user_id: Annotated[int, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> None:
    user = await get_profile(db, current_user_id)
    await change_password(db, user, body)


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="회원 탈퇴",
)
async def delete_my_account(
    response: Response,
    current_user_id: Annotated[int, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> None:
    user = await get_profile(db, current_user_id)
    await delete_account(db, user)

    response.delete_cookie(
        key="refresh_token",
        path="/",
        httponly=True,
        secure=False,
        samesite="lax",
    )


@router.patch(
    "/{user_id}/role",
    response_model=RoleChangeResponse,
    status_code=status.HTTP_200_OK,
    summary="회원 권한 변경",
)
async def update_user_role(
    user_id: int,
    body: RoleChangeRequest,
    current_user_id: Annotated[int, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> User:
    current_user = await get_profile(db, current_user_id)
    return await change_user_role(db, current_user, user_id, body.role)