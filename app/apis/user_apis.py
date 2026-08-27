from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, Query, Response, status

from app.apis.dependencies import CurrentAdmin, CurrentUser, DatabaseSession
from app.core.config import settings
from app.core.security import (
    TokenValidationError,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    PasswordChangeRequest,
    RoleBulkUpdateRequest,
    RoleBulkUpdateResponse,
    TokenResponse,
    UserListQuery,
    UserListResponse,
    UserLoginRequest,
    UserProfileUpdateRequest,
    UserResponse,
    UserSignupRequest,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/api/v1")
auth_router = APIRouter(prefix="/auth", tags=["user-auth"])
user_router = APIRouter(prefix="/users", tags=["users"])
admin_router = APIRouter(prefix="/admin/users", tags=["admin-users"])


def _token_response(user_id: int) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user_id),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/auth",
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
    )


def _delete_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path="/api/v1/auth",
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
    )


@auth_router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="회원가입",
)
async def signup(body: UserSignupRequest, db: DatabaseSession):
    return await UserService.signup(db, body)


@auth_router.post(
    "/login",
    response_model=TokenResponse,
    summary="로그인",
)
async def login(body: UserLoginRequest, response: Response, db: DatabaseSession):
    user = await UserService.authenticate(db, body)
    _set_refresh_cookie(response, create_refresh_token(user.id))
    return _token_response(user.id)


@auth_router.post(
    "/token/refresh",
    response_model=TokenResponse,
    summary="Access Token 재발급",
)
async def refresh_access_token(
    db: DatabaseSession,
    refresh_token: str | None = Cookie(
        default=None, alias=settings.REFRESH_COOKIE_NAME
    ),
):
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="유효한 Refresh Token이 필요합니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if refresh_token is None:
        raise unauthorized

    try:
        payload = decode_token(refresh_token, "refresh")
    except TokenValidationError as exc:
        raise unauthorized from exc

    user = await UserRepository.get_by_id(db, payload.user_id)
    if user is None:
        raise unauthorized
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다.",
        )
    return _token_response(user.id)


@auth_router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="로그아웃",
)
async def logout() -> Response:
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _delete_refresh_cookie(response)
    return response


@admin_router.get(
    "",
    response_model=UserListResponse,
    summary="관리자 회원 목록 조회",
)
async def list_users(
    query: Annotated[UserListQuery, Query()],
    db: DatabaseSession,
    _admin: CurrentAdmin,
) -> UserListResponse:
    users, total = await UserService.list_users(db, query)
    return UserListResponse(
        items=[UserResponse.model_validate(user) for user in users],
        total=total,
        page=query.page,
        size=query.size,
    )


@admin_router.patch(
    "/roles",
    response_model=RoleBulkUpdateResponse,
    summary="관리자 회원 권한 일괄 변경",
)
async def update_user_roles(
    body: RoleBulkUpdateRequest,
    db: DatabaseSession,
    _admin: CurrentAdmin,
) -> RoleBulkUpdateResponse:
    updated_count = await UserService.update_roles(db, body)
    return RoleBulkUpdateResponse(updated_count=updated_count, role=body.role)


@user_router.get(
    "/me",
    response_model=UserResponse,
    summary="마이페이지 조회",
)
async def get_my_profile(current_user: CurrentUser):
    return current_user


@user_router.patch(
    "/me",
    response_model=UserResponse,
    summary="회원 정보 수정",
)
async def update_my_profile(
    body: UserProfileUpdateRequest,
    db: DatabaseSession,
    current_user: CurrentUser,
):
    return await UserService.update_profile(db, current_user, body)


@user_router.patch(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="비밀번호 변경",
)
async def change_my_password(
    body: PasswordChangeRequest,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> Response:
    await UserService.change_password(db, current_user, body)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@user_router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="회원 탈퇴",
)
async def delete_my_account(
    db: DatabaseSession,
    current_user: CurrentUser,
) -> Response:
    await UserService.delete_user(db, current_user)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _delete_refresh_cookie(response)
    return response


router.include_router(auth_router)
router.include_router(user_router)
router.include_router(admin_router)
