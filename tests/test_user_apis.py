from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.core.db.databases import Base, async_get_db
from app.core.security import decode_token, hash_password
from app.main import app
from app.models import Department, Gender, Role, User

TEST_DATABASE_URL = "sqlite+aiosqlite://"


@pytest_asyncio.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncClient]:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[async_get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()


async def create_admin(
    session_factory: async_sessionmaker[AsyncSession],
) -> User:
    async with session_factory() as session:
        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("AdminPassword1!"),
            name="관리자",
            department=Department.DEV,
            gender=Gender.F,
            phone_number="01099998888",
            role=Role.ADMIN,
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        return admin


async def signup_user(client: AsyncClient) -> dict:
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "Staff@Example.com",
            "password": "Password1!",
            "name": "홍길동",
            "department": "MEDICAL",
            "gender": "M",
            "phone_number": "010-1234-5678",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def login(
    client: AsyncClient,
    email: str,
    password: str,
) -> tuple[str, object]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"], response


@pytest.mark.asyncio
async def test_auth_and_profile_lifecycle(client: AsyncClient) -> None:
    created = await signup_user(client)
    assert created["email"] == "staff@example.com"
    assert created["phone_number"] == "01012345678"
    assert created["role"] == "PENDING"
    assert "password" not in created
    assert "hashed_password" not in created

    duplicate = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "staff@example.com",
            "password": "Password1!",
            "name": "다른회원",
            "department": "RESEARCH",
            "gender": "F",
            "phone_number": "01011112222",
        },
    )
    assert duplicate.status_code == 409

    access_token, login_response = await login(
        client, "STAFF@example.com", "Password1!"
    )
    cookie_header = login_response.headers["set-cookie"]
    assert "HttpOnly" in cookie_header
    assert "Max-Age=604800" in cookie_header
    assert "Path=/api/v1/auth" in cookie_header

    payload = decode_token(access_token, "access")
    assert payload.user_id == created["id"]
    assert set(payload.model_dump()) == {"user_id", "token_type", "iat", "exp"}

    headers = {"Authorization": f"Bearer {access_token}"}
    profile = await client.get("/api/v1/users/me", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["name"] == "홍길동"

    empty_update = await client.patch("/api/v1/users/me", headers=headers, json={})
    assert empty_update.status_code == 400

    updated = await client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={
            "department": "RESEARCH",
            "phone_number": "010-7777-8888",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["department"] == "RESEARCH"
    assert updated.json()["phone_number"] == "01077778888"

    wrong_password = await client.patch(
        "/api/v1/users/me/password",
        headers=headers,
        json={
            "current_password": "WrongPassword1!",
            "new_password": "NewPassword2@",
        },
    )
    assert wrong_password.status_code == 400

    changed = await client.patch(
        "/api/v1/users/me/password",
        headers=headers,
        json={
            "current_password": "Password1!",
            "new_password": "NewPassword2@",
        },
    )
    assert changed.status_code == 204

    old_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "staff@example.com", "password": "Password1!"},
    )
    assert old_login.status_code == 401
    new_access_token, _ = await login(client, "staff@example.com", "NewPassword2@")

    refreshed = await client.post("/api/v1/auth/token/refresh")
    assert refreshed.status_code == 200
    assert (
        decode_token(refreshed.json()["access_token"], "access").user_id
        == created["id"]
    )

    logout = await client.post("/api/v1/auth/logout")
    assert logout.status_code == 204
    assert "Max-Age=0" in logout.headers["set-cookie"]

    deleted = await client.delete(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {new_access_token}"},
    )
    assert deleted.status_code == 204

    deleted_profile = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {new_access_token}"},
    )
    assert deleted_profile.status_code == 401


@pytest.mark.asyncio
async def test_admin_list_filter_and_bulk_role_update(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await create_admin(session_factory)
    created = await signup_user(client)

    pending_access_token, _ = await login(client, "staff@example.com", "Password1!")
    denied = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {pending_access_token}"},
    )
    assert denied.status_code == 403

    admin_access_token, _ = await login(client, "admin@example.com", "AdminPassword1!")
    admin_headers = {"Authorization": f"Bearer {admin_access_token}"}

    users = await client.get(
        "/api/v1/admin/users",
        params={"search": "staff", "department": "MEDICAL"},
        headers=admin_headers,
    )
    assert users.status_code == 200, users.text
    assert users.json()["total"] == 1
    assert users.json()["items"][0]["id"] == created["id"]

    missing = await client.patch(
        "/api/v1/admin/users/roles",
        headers=admin_headers,
        json={"user_ids": [created["id"], 9999], "role": "STAFF"},
    )
    assert missing.status_code == 404
    assert missing.json()["detail"]["missing_user_ids"] == [9999]

    changed = await client.patch(
        "/api/v1/admin/users/roles",
        headers=admin_headers,
        json={"user_ids": [created["id"]], "role": "STAFF"},
    )
    assert changed.status_code == 200
    assert changed.json() == {"updated_count": 1, "role": "STAFF"}

    profile = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {pending_access_token}"},
    )
    assert profile.status_code == 200
    assert profile.json()["role"] == "STAFF"


@pytest.mark.asyncio
async def test_validation_and_invalid_tokens(client: AsyncClient) -> None:
    weak_password = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "weak@example.com",
            "password": "password",
            "name": "검증회원",
            "department": "DEV",
            "gender": "F",
            "phone_number": "01011112222",
        },
    )
    assert weak_password.status_code == 422

    invalid_phone = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "phone@example.com",
            "password": "Password1!",
            "name": "검증회원",
            "department": "DEV",
            "gender": "F",
            "phone_number": "0212345678",
        },
    )
    assert invalid_phone.status_code == 422

    no_token = await client.get("/api/v1/users/me")
    assert no_token.status_code == 401

    bad_token = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert bad_token.status_code == 401

    no_refresh_cookie = await client.post("/api/v1/auth/token/refresh")
    assert no_refresh_cookie.status_code == 401
