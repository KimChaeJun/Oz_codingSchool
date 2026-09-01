import itertools
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import BigInteger, func, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool

import app.core.storage as storage
import app.services.prediction_service as prediction_service_module
from app.core.db.databases import Base, async_get_db
from app.core.security import hash_password
from app.main import app
from app.models import (
    AiAnalysisResult,
    Department,
    Gender,
    MedicalRecord,
    Patient,
    Role,
    User,
    XrayImage,
)
from worker.model import MODEL_VERSION, PneumoniaPrediction

TEST_DATABASE_URL = "sqlite+aiosqlite://"
_phone_number_sequence = itertools.count(1)


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
) -> User:
    async with session_factory() as session:
        user = User(
            email=email,
            hashed_password=hash_password("Password1!"),
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


async def login(client: AsyncClient, email: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password1!"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def create_medical_record(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    uploader_id: int,
    image_url: str | None,
) -> MedicalRecord:
    async with session_factory() as session:
        patient = Patient(
            name="홍길동",
            age=40,
            gender=Gender.M,
            phone=f"011{next(_phone_number_sequence):08d}",
        )
        session.add(patient)
        await session.flush()

        record = MedicalRecord(
            patient_id=patient.id,
            chart_number=f"CHART-{next(_phone_number_sequence)}",
            symptoms="발열과 기침",
        )
        session.add(record)
        await session.flush()

        if image_url is not None:
            session.add(
                XrayImage(
                    record_id=record.id,
                    uploader_id=uploader_id,
                    image_url=image_url,
                    shooting_datetime=datetime.now(UTC).replace(tzinfo=None),
                )
            )

        await session.commit()
        await session.refresh(record)
        return record


@pytest.mark.asyncio
async def test_prediction_is_saved_once_and_then_reused(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    staff = await create_user(
        session_factory,
        email="staff@example.com",
        role=Role.STAFF,
    )
    headers = await login(client, staff.email)

    monkeypatch.setattr(storage, "MEDIA_ROOT", tmp_path)
    image_path = tmp_path / "xray" / "record-1.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"test-xray")

    record = await create_medical_record(
        session_factory,
        uploader_id=staff.id,
        image_url="/media/xray/record-1.png",
    )

    inference_count = 0

    def fake_predict(image: Path) -> PneumoniaPrediction:
        nonlocal inference_count
        inference_count += 1
        assert image == image_path
        return PneumoniaPrediction(
            is_pneumonia=True,
            confidence=92.0842,
            pneumonia_probability=0.920842,
            model_version=MODEL_VERSION,
        )

    monkeypatch.setattr(
        prediction_service_module.pneumonia_predictor,
        "predict",
        fake_predict,
    )

    endpoint = f"/api/v1/medical-records/{record.id}/predictions"
    created = await client.post(endpoint, headers=headers)
    assert created.status_code == 201, created.text
    assert created.json() == {
        "id": 1,
        "record_id": record.id,
        "is_pneumonia": True,
        "confidence": 92.08,
        "heatmap_url": None,
        "predicted_at": created.json()["predicted_at"],
        "model": MODEL_VERSION,
        "cached": False,
    }

    cached = await client.post(endpoint, headers=headers)
    assert cached.status_code == 200, cached.text
    assert cached.json()["id"] == created.json()["id"]
    assert cached.json()["cached"] is True
    assert inference_count == 1

    listed = await client.get(endpoint, headers=headers)
    assert listed.status_code == 200, listed.text
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == created.json()["id"]
    assert "cached" not in listed.json()[0]

    async with session_factory() as session:
        count = await session.scalar(select(func.count(AiAnalysisResult.id)))
        assert count == 1


@pytest.mark.asyncio
async def test_prediction_requires_staff_role(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    pending = await create_user(
        session_factory,
        email="pending@example.com",
        role=Role.PENDING,
    )
    headers = await login(client, pending.email)

    response = await client.post(
        "/api/v1/medical-records/1/predictions",
        headers=headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_prediction_returns_not_found_for_unknown_record(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    staff = await create_user(
        session_factory,
        email="staff@example.com",
        role=Role.STAFF,
    )
    headers = await login(client, staff.email)

    response = await client.post(
        "/api/v1/medical-records/999999/predictions",
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_prediction_requires_stored_xray(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    staff = await create_user(
        session_factory,
        email="staff@example.com",
        role=Role.STAFF,
    )
    headers = await login(client, staff.email)
    record = await create_medical_record(
        session_factory,
        uploader_id=staff.id,
        image_url=None,
    )

    response = await client.post(
        f"/api/v1/medical-records/{record.id}/predictions",
        headers=headers,
    )
    assert response.status_code == 409
    assert "X-Ray" in response.json()["detail"]
