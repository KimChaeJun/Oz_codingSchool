from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, create_refresh_token
from app.models.user import RoleEnum, User
from app.repositories.user import (
    create_user,
    get_user_by_email,
    get_user_by_phone_number,
    get_user_by_id,
    update_user,
    delete_user,
    get_all_users,
)
from app.schemas.user import UserCreateRequest, TokenResponse, UserUpdateRequest, PasswordChangeRequest


password_hasher = PasswordHasher()


async def register_user(
    db: AsyncSession,
    body: UserCreateRequest,
) -> User:
    existing_email = await get_user_by_email(db, body.email)

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 이메일입니다.",
        )

    existing_phone_number = await get_user_by_phone_number(
        db,
        body.phone_number,
    )

    if existing_phone_number:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 휴대폰 번호입니다.",
        )

    hashed_password = password_hasher.hash(body.password)

    user = User(
        email=body.email,
        hashed_password=hashed_password,
        name=body.name,
        phone_number=body.phone_number,
        gender=body.gender,
        department=body.department,
        role=RoleEnum.PENDING,
    )

    try:
        return await create_user(db, user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 이메일 또는 휴대폰 번호입니다.",
        )


async def login_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> TokenResponse:
    user = await get_user_by_email(db, email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    try:
        password_hasher.verify(user.hashed_password, password)
    except (VerifyMismatchError, VerificationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다.",
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token,
    )


async def get_profile(
    db: AsyncSession,
    user_id: int,
) -> User:
    user = await get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다.",
        )

    return user


async def update_profile(
    db: AsyncSession,
    user: User,
    body: UserUpdateRequest,
) -> User:
    if body.phone_number:
        existing_phone = await get_user_by_phone_number(db, body.phone_number)
        if existing_phone and existing_phone.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 등록된 휴대폰 번호입니다.",
            )
        user.phone_number = body.phone_number

    if body.department:
        user.department = body.department

    try:
        return await update_user(db, user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 휴대폰 번호입니다.",
        )


async def change_password(
    db: AsyncSession,
    user: User,
    body: PasswordChangeRequest,
) -> None:
    try:
        password_hasher.verify(user.hashed_password, body.current_password)
    except (VerifyMismatchError, VerificationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="기존 비밀번호가 일치하지 않습니다.",
        )

    user.hashed_password = password_hasher.hash(body.new_password)
    await update_user(db, user)


async def delete_account(
    db: AsyncSession,
    user: User,
) -> None:
    await delete_user(db, user)


async def list_users(
    db: AsyncSession,
    current_user: User,
    search: str | None = None,
    department: str | None = None,
) -> list[User]:
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ADMIN 권한이 없습니다.",
        )

    return await get_all_users(db, search, department)


async def change_user_role(
    db: AsyncSession,
    current_user: User,
    target_user_id: int,
    new_role: RoleEnum,
) -> User:
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ADMIN 권한이 없습니다.",
        )

    target_user = await get_user_by_id(db, target_user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다.",
        )

    target_user.role = new_role
    return await update_user(db, target_user)