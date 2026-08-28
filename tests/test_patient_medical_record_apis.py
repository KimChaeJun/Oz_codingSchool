import itertools
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import BigInteger
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import StaticPool

from app.core.db.databases import Base, async_get_db
from app.core.security import hash_password
from app.main import app
from app.models import Department, Gender, MedicalRecord, Role, User

TEST_DATABASE_URL = "sqlite+aiosqlite://"
FAKE_JPEG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
_phone_number_sequence = itertools.count(1)


# SQLite는 BigInteger PK를 rowid 별칭(autoincrement)으로 인식하지 않는다.
# Patient/MedicalRecord/XrayImage는 실제 MySQL에서는 정상 동작하므로 모델은
# 그대로 두고, 테스트 DB(SQLite)에서만 INTEGER로 렌더링되도록 우회한다.
@compiles(BigInteger, "sqlite")
def _compile_big_integer_as_integer(type_, compiler, **kw):
    return "INTEGER"


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


async def create_user(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    email: str,
    role: Role,
    password: str = "Password1!",
) -> User:
    async with session_factory() as session:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            name="테스트유저",
            department=Department.MEDICAL,
            gender=Gender.F,
            phone_number=f"010{next(_phone_number_sequence):08d}",
            role=role,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def login(client: AsyncClient, email: str, password: str = "Password1!") -> str:
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_register_patient_requires_staff_or_admin(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await create_user(session_factory, email="pending@example.com", role=Role.PENDING)
    await create_user(session_factory, email="staff@example.com", role=Role.STAFF)

    pending_token = await login(client, "pending@example.com")
    denied = await client.post(
        "/api/v1/patients",
        headers=auth_headers(pending_token),
        json={"name": "홍길동", "age": 40, "gender": "M", "phone": "01012345678"},
    )
    assert denied.status_code == 403

    staff_token = await login(client, "staff@example.com")
    created = await client.post(
        "/api/v1/patients",
        headers=auth_headers(staff_token),
        json={"name": "홍길동", "age": 40, "gender": "M", "phone": "01012345678"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["name"] == "홍길동"
    assert body["phone"] == "01012345678"
    assert "id" in body and "created_at" in body


@pytest.mark.asyncio
async def test_patient_validation(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await create_user(session_factory, email="staff@example.com", role=Role.STAFF)
    token = await login(client, "staff@example.com")

    invalid_age = await client.post(
        "/api/v1/patients",
        headers=auth_headers(token),
        json={"name": "홍길동", "age": 200, "gender": "M", "phone": "01012345678"},
    )
    assert invalid_age.status_code == 422

    invalid_phone = await client.post(
        "/api/v1/patients",
        headers=auth_headers(token),
        json={"name": "홍길동", "age": 40, "gender": "M", "phone": "0212345678"},
    )
    assert invalid_phone.status_code == 422

    extra_field = await client.post(
        "/api/v1/patients",
        headers=auth_headers(token),
        json={
            "name": "홍길동",
            "age": 40,
            "gender": "M",
            "phone": "01012345678",
            "note": "허용 안 됨",
        },
    )
    assert extra_field.status_code == 422


@pytest.mark.asyncio
async def test_patient_crud_lifecycle(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await create_user(session_factory, email="staff@example.com", role=Role.STAFF)
    token = await login(client, "staff@example.com")
    headers = auth_headers(token)

    created = await client.post(
        "/api/v1/patients",
        headers=headers,
        json={"name": "홍길동", "age": 40, "gender": "M", "phone": "010-1234-5678"},
    )
    assert created.status_code == 201
    patient_id = created.json()["id"]
    assert created.json()["phone"] == "01012345678"

    await client.post(
        "/api/v1/patients",
        headers=headers,
        json={"name": "김철수", "age": 20, "gender": "F", "phone": "01099998888"},
    )

    search_result = await client.get(
        "/api/v1/patients", params={"search": "홍길동"}, headers=headers
    )
    assert search_result.status_code == 200
    assert len(search_result.json()) == 1
    assert search_result.json()[0]["id"] == patient_id

    gender_filter = await client.get(
        "/api/v1/patients", params={"gender": "F"}, headers=headers
    )
    assert len(gender_filter.json()) == 1
    assert gender_filter.json()[0]["name"] == "김철수"

    age_filter = await client.get(
        "/api/v1/patients",
        params={"age_min": 30, "age_max": 50},
        headers=headers,
    )
    assert len(age_filter.json()) == 1
    assert age_filter.json()[0]["id"] == patient_id

    detail = await client.get(f"/api/v1/patients/{patient_id}", headers=headers)
    assert detail.status_code == 200
    assert set(detail.json().keys()) == {"name", "gender", "phone", "age"}

    updated = await client.patch(
        f"/api/v1/patients/{patient_id}",
        headers=headers,
        json={"phone": "01000001111"},
    )
    assert updated.status_code == 200
    assert updated.json()["phone"] == "01000001111"
    assert updated.json()["name"] == "홍길동"

    forbidden_update = await client.patch(
        f"/api/v1/patients/{patient_id}",
        headers=headers,
        json={"age": 99},
    )
    assert forbidden_update.status_code == 422

    missing = await client.get("/api/v1/patients/999999", headers=headers)
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_medical_record_lifecycle(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    staff = await create_user(session_factory, email="staff@example.com", role=Role.STAFF)
    token = await login(client, "staff@example.com")
    headers = auth_headers(token)

    patient = await client.post(
        "/api/v1/patients",
        headers=headers,
        json={"name": "홍길동", "age": 40, "gender": "M", "phone": "01012345678"},
    )
    patient_id = patient.json()["id"]

    long_symptoms = "가" * 150

    created = await client.post(
        "/api/v1/medical-records",
        headers=headers,
        data={
            "patient_id": patient_id,
            "chart_number": "CN-0001",
            "symptoms": long_symptoms,
        },
        files={"xray_image": ("xray.jpg", FAKE_JPEG, "image/jpeg")},
    )
    assert created.status_code == 201, created.text
    record_id = created.json()["id"]
    assert created.json()["symptoms"] == long_symptoms
    assert len(created.json()["xray_images"]) == 1
    image_url = created.json()["xray_images"][0]
    saved_path = Path(__file__).resolve().parent.parent / image_url.lstrip("/")
    assert saved_path.exists()

    async with session_factory() as session:
        stored_record = await session.get(
            MedicalRecord, record_id, options=[selectinload(MedicalRecord.xray_images)]
        )
        assert stored_record.xray_images[0].uploader_id == staff.id

    duplicate = await client.post(
        "/api/v1/medical-records",
        headers=headers,
        data={
            "patient_id": patient_id,
            "chart_number": "CN-0001",
            "symptoms": "중복 테스트",
        },
        files={"xray_image": ("xray2.jpg", FAKE_JPEG, "image/jpeg")},
    )
    assert duplicate.status_code == 409

    missing_patient = await client.post(
        "/api/v1/medical-records",
        headers=headers,
        data={
            "patient_id": 999999,
            "chart_number": "CN-0002",
            "symptoms": "환자 없음 테스트",
        },
        files={"xray_image": ("xray3.jpg", FAKE_JPEG, "image/jpeg")},
    )
    assert missing_patient.status_code == 404

    invalid_type = await client.post(
        "/api/v1/medical-records",
        headers=headers,
        data={
            "patient_id": patient_id,
            "chart_number": "CN-0003",
            "symptoms": "잘못된 파일 형식",
        },
        files={"xray_image": ("xray.txt", b"not-an-image", "text/plain")},
    )
    assert invalid_type.status_code == 422

    list_response = await client.get(
        f"/api/v1/patients/{patient_id}/medical-records", headers=headers
    )
    assert list_response.status_code == 200
    items = list_response.json()
    assert len(items) == 1
    assert items[0]["symptoms"] == "가" * 100 + "…"
    assert "xray_images" not in items[0]

    detail = await client.get(f"/api/v1/medical-records/{record_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["symptoms"] == long_symptoms

    missing_record = await client.get(
        "/api/v1/medical-records/999999", headers=headers
    )
    assert missing_record.status_code == 404


@pytest.mark.asyncio
async def test_patient_delete_removes_records_and_files(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await create_user(session_factory, email="staff@example.com", role=Role.STAFF)
    token = await login(client, "staff@example.com")
    headers = auth_headers(token)

    patient = await client.post(
        "/api/v1/patients",
        headers=headers,
        json={"name": "홍길동", "age": 40, "gender": "M", "phone": "01012345678"},
    )
    patient_id = patient.json()["id"]

    created = await client.post(
        "/api/v1/medical-records",
        headers=headers,
        data={
            "patient_id": patient_id,
            "chart_number": "CN-DEL-001",
            "symptoms": "삭제 테스트",
        },
        files={"xray_image": ("xray.jpg", FAKE_JPEG, "image/jpeg")},
    )
    record_id = created.json()["id"]
    image_url = created.json()["xray_images"][0]
    saved_path = Path(__file__).resolve().parent.parent / image_url.lstrip("/")
    assert saved_path.exists()

    deleted = await client.delete(f"/api/v1/patients/{patient_id}", headers=headers)
    assert deleted.status_code == 204

    assert not saved_path.exists()

    missing_patient = await client.get(
        f"/api/v1/patients/{patient_id}", headers=headers
    )
    assert missing_patient.status_code == 404

    missing_record = await client.get(
        f"/api/v1/medical-records/{record_id}", headers=headers
    )
    assert missing_record.status_code == 404


@pytest.mark.asyncio
async def test_medical_record_endpoints_require_staff_or_admin(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await create_user(session_factory, email="staff@example.com", role=Role.STAFF)
    await create_user(session_factory, email="pending@example.com", role=Role.PENDING)

    staff_token = await login(client, "staff@example.com")
    patient = await client.post(
        "/api/v1/patients",
        headers=auth_headers(staff_token),
        json={"name": "홍길동", "age": 40, "gender": "M", "phone": "01012345678"},
    )
    patient_id = patient.json()["id"]

    pending_token = await login(client, "pending@example.com")
    pending_headers = auth_headers(pending_token)

    denied_register = await client.post(
        "/api/v1/medical-records",
        headers=pending_headers,
        data={
            "patient_id": patient_id,
            "chart_number": "CN-DENIED",
            "symptoms": "권한 없음 테스트",
        },
        files={"xray_image": ("xray.jpg", FAKE_JPEG, "image/jpeg")},
    )
    assert denied_register.status_code == 403

    denied_list = await client.get(
        f"/api/v1/patients/{patient_id}/medical-records", headers=pending_headers
    )
    assert denied_list.status_code == 403
