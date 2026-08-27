from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    DUMMY_PASSWORD_HASH,
    hash_password,
    verify_password,
)
from app.models import Role, User
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    PasswordChangeRequest,
    RoleBulkUpdateRequest,
    UserListQuery,
    UserLoginRequest,
    UserProfileUpdateRequest,
    UserSignupRequest,
)


class UserService:
    @staticmethod
    async def _commit(db: AsyncSession, duplicate_detail: str) -> None:
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=duplicate_detail,
            ) from exc

    @classmethod
    async def signup(cls, db: AsyncSession, body: UserSignupRequest) -> User:
        email = str(body.email)
        if await UserRepository.get_by_email(db, email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 가입된 이메일입니다.",
            )
        if await UserRepository.get_by_phone_number(db, body.phone_number):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 가입된 휴대폰 번호입니다.",
            )

        user = User(
            email=email,
            hashed_password=hash_password(body.password.get_secret_value()),
            name=body.name,
            department=body.department,
            gender=body.gender,
            phone_number=body.phone_number,
            role=Role.PENDING,
            is_active=True,
        )
        db.add(user)
        await cls._commit(db, "이미 사용 중인 이메일 또는 휴대폰 번호입니다.")
        await db.refresh(user)
        return user

    @staticmethod
    async def authenticate(db: AsyncSession, body: UserLoginRequest) -> User:
        user = await UserRepository.get_by_email(db, str(body.email))
        plain_password = body.password.get_secret_value()

        if user is None:
            verify_password(plain_password, DUMMY_PASSWORD_HASH)
        if user is None or not verify_password(plain_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="이메일 또는 비밀번호가 올바르지 않습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="비활성화된 계정입니다.",
            )
        return user

    @staticmethod
    async def list_users(
        db: AsyncSession, query: UserListQuery
    ) -> tuple[list[User], int]:
        return await UserRepository.list_users(
            db,
            search=query.search,
            department=query.department,
            page=query.page,
            size=query.size,
        )

    @classmethod
    async def update_roles(cls, db: AsyncSession, body: RoleBulkUpdateRequest) -> int:
        users = await UserRepository.get_by_ids(db, body.user_ids)
        found_ids = {user.id for user in users}
        missing_ids = sorted(set(body.user_ids) - found_ids)
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "권한 변경 대상 회원을 찾을 수 없습니다.",
                    "missing_user_ids": missing_ids,
                },
            )

        for user in users:
            user.role = body.role
        await cls._commit(db, "회원 권한 변경 중 충돌이 발생했습니다.")
        return len(users)

    @classmethod
    async def update_profile(
        cls,
        db: AsyncSession,
        user: User,
        body: UserProfileUpdateRequest,
    ) -> User:
        updates = body.model_dump(exclude_unset=True, exclude_none=True)
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="수정할 항목을 하나 이상 입력해야 합니다.",
            )

        phone_number = updates.get("phone_number")
        if phone_number and phone_number != user.phone_number:
            registered_user = await UserRepository.get_by_phone_number(db, phone_number)
            if registered_user:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="이미 가입된 휴대폰 번호입니다.",
                )

        for field, value in updates.items():
            setattr(user, field, value)
        await cls._commit(db, "이미 사용 중인 휴대폰 번호입니다.")
        await db.refresh(user)
        return user

    @classmethod
    async def change_password(
        cls,
        db: AsyncSession,
        user: User,
        body: PasswordChangeRequest,
    ) -> None:
        current_password = body.current_password.get_secret_value()
        new_password = body.new_password.get_secret_value()
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="현재 비밀번호가 일치하지 않습니다.",
            )
        if verify_password(new_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="새 비밀번호는 현재 비밀번호와 달라야 합니다.",
            )

        user.hashed_password = hash_password(new_password)
        await cls._commit(db, "비밀번호 변경 중 충돌이 발생했습니다.")

    @staticmethod
    async def delete_user(db: AsyncSession, user: User) -> None:
        await db.delete(user)
        await db.commit()
