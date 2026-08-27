from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Department, User


class UserRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int) -> User | None:
        return await db.get(User, user_id)

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return await db.scalar(statement)

    @staticmethod
    async def get_by_phone_number(db: AsyncSession, phone_number: str) -> User | None:
        statement = select(User).where(User.phone_number == phone_number)
        return await db.scalar(statement)

    @staticmethod
    async def get_by_ids(db: AsyncSession, user_ids: list[int]) -> list[User]:
        statement = select(User).where(User.id.in_(user_ids))
        result = await db.scalars(statement)
        return list(result.all())

    @staticmethod
    async def list_users(
        db: AsyncSession,
        *,
        search: str | None,
        department: Department | None,
        page: int,
        size: int,
    ) -> tuple[list[User], int]:
        filters = []
        if search:
            keyword = f"%{search.casefold()}%"
            filters.append(
                or_(
                    func.lower(User.email).like(keyword),
                    func.lower(User.name).like(keyword),
                )
            )
        if department:
            filters.append(User.department == department)

        count_statement = select(func.count(User.id)).where(*filters)
        total = int(await db.scalar(count_statement) or 0)

        statement = (
            select(User)
            .where(*filters)
            .order_by(User.email.asc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await db.scalars(statement)
        return list(result.all()), total
