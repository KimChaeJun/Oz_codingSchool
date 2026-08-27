from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_user_by_email(
    db: AsyncSession,
    email: str,
) -> User | None:
    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def get_user_by_phone_number(
    db: AsyncSession,
    phone_number: str,
) -> User | None:
    result = await db.execute(
        select(User).where(User.phone_number == phone_number)
    )
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    user: User,
) -> User:
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_id(
    db: AsyncSession,
    user_id: int,
) -> User | None:
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def update_user(
    db: AsyncSession,
    user: User,
) -> User:
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(
    db: AsyncSession,
    user: User,
) -> None:
    await db.delete(user)
    await db.commit()


async def get_all_users(
    db: AsyncSession,
    search: str | None = None,
    department: str | None = None,
) -> list[User]:
    query = select(User)

    if search:
        query = query.where(
            (User.email.contains(search)) | (User.name.contains(search))
        )

    if department:
        query = query.where(User.department == department)

    result = await db.execute(query)
    return result.scalars().all()