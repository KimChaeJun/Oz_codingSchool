from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.auth_service import get_current_user
from app.schemas.user_schema import (
    PasswordChange,
    RoleUpdate,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserStatusUpdate,
    UserUpdate,
)

from app.core.db.databases import async_get_db
from app.models.user import Department, Role, User
from app.schemas.user_schema import (
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.password_service import PasswordService
from app.services.token_service import TokenService


router = APIRouter(
    prefix="/api/v1",
    tags=["User"],
)


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="회원가입",
)
async def register_user(
    body: UserCreate,
    db: AsyncSession = Depends(async_get_db),
):
    result = await db.execute(
        select(User).where(User.email == body.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 가입된 이메일입니다.",
        )

    user = User(
        email=body.email,
        hashed_password=PasswordService.hash_password(body.password),
        name=body.name,
        department=body.department,
        gender=body.gender,
        phone_number=body.phone_number,
        role=Role.PENDING,
        is_active=True,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    summary="로그인",
)
async def login_user(
    body: UserLogin,
    response: Response,
    db: AsyncSession = Depends(async_get_db),
):
    result = await db.execute(
        select(User).where(User.email == body.email)
    )
    user = result.scalar_one_or_none()

    if user is None or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    if not PasswordService.verify_password(
        body.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 사용자입니다.",
        )

    access_token = TokenService.create_access_token(user.id)
    refresh_token = TokenService.create_refresh_token(user.id)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
    )

@router.get(
    "/users/me",
    response_model=UserResponse,
    summary="내 정보 조회",
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user

@router.post(
    "/auth/refresh",
    response_model=TokenResponse,
    summary="액세스 토큰 재발급",
)
async def refresh_access_token(
    refresh_token: str | None = Cookie(default=None),
):
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="리프레시 토큰이 없습니다.",
        )

    try:
        payload = TokenService.decode_token(refresh_token)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 리프레시 토큰입니다.",
        )

    user_id = payload.get("user_id")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰에 사용자 정보가 없습니다.",
        )

    access_token = TokenService.create_access_token(user_id)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
    )


@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="로그아웃",
)
async def logout_user(
    response: Response,
):
    response.delete_cookie("refresh_token")


@router.patch(
    "/users/me",
    response_model=UserResponse,
    summary="내 정보 수정",
)
async def update_my_profile(
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    if body.department is not None:
        current_user.department = body.department

    if body.phone_number is not None:
        current_user.phone_number = body.phone_number

    await db.commit()
    await db.refresh(current_user)

    return current_user


@router.patch(
    "/users/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="비밀번호 변경",
)
async def change_my_password(
    body: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    if current_user.hashed_password is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 설정되어 있지 않습니다.",
        )

    if not PasswordService.verify_password(
        body.current_password,
        current_user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 올바르지 않습니다.",
        )

    current_user.hashed_password = PasswordService.hash_password(
        body.new_password
    )

    await db.commit()


@router.delete(
    "/users/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="회원 탈퇴",
)
async def delete_my_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    await db.delete(current_user)
    await db.commit()

def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다.",
        )

    return current_user


@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="회원 목록 조회",
)
async def get_users(
    name: str | None = Query(default=None),
    email: str | None = Query(default=None),
    department: Department | None = Query(default=None),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(async_get_db),
):
    stmt = select(User)

    if name:
        stmt = stmt.where(User.name.contains(name))

    if email:
        stmt = stmt.where(User.email.contains(email))

    if department:
        stmt = stmt.where(User.department == department)

    result = await db.execute(stmt)

    return result.scalars().all()


@router.patch(
    "/users/{user_id}/role",
    response_model=UserResponse,
    summary="회원 권한 변경",
)
async def update_user_role(
    user_id: int,
    body: RoleUpdate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(async_get_db),
):
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다.",
        )

    user.role = body.role

    await db.commit()
    await db.refresh(user)

    return user

@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="회원 단일 조회",
)
async def get_user(
    user_id: int,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(async_get_db),
):
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다.",
        )

    return user


@router.patch(
    "/users/{user_id}/status",
    response_model=UserResponse,
    summary="회원 활성화 상태 변경",
)
async def update_user_status(
    user_id: int,
    body: UserStatusUpdate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(async_get_db),
):
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다.",
        )

    user.is_active = body.is_active

    await db.commit()
    await db.refresh(user)

    return user