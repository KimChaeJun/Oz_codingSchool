import itertools
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import BigInteger, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import StaticPool

import app.core.storage as storage
from app.core.db.databases import Base, async_get_db
from app.core.security import hash_password
from app.main import app
from app.models import Department, Gender, MedicalRecord, Patient, Role, User
from app.services.medical_record_service import MedicalRecordService
from app.services.patient_service import PatientService

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


class FakeUploadFile:
    """save_xray_image가 실제로 쓰는 content_type/read()만 흉내내는 최소 더미."""

    def __init__(self, content: bytes, content_type: str):
        self.content_type = content_type
        self._content = content

    async def read(self) -> bytes:
        return self._content


@pytest.mark.asyncio
async def test_patient_with_null_gender_serializes_as_null(
    session_factory: async_sessionmaker[AsyncSession],
    client: AsyncClient,
) -> None:
    """Patient.gender는 DB상 nullable이다. 응답 스키마가 Gender | None으로
    바뀐 뒤에는 NULL gender 행이 있어도 정상 응답(gender: null)이어야 한다."""
    await create_user(session_factory, email="staff-null@example.com", role=Role.STAFF)
    async with session_factory() as session:
        patient = Patient(name="무성별환자", age=30, gender=None, phone="01000009999")
        session.add(patient)
        await session.commit()
        await session.refresh(patient)
        patient_id = patient.id

    token = await login(client, "staff-null@example.com")
    headers = auth_headers(token)

    list_response = await client.get("/api/v1/patients", headers=headers)
    detail_response = await client.get(f"/api/v1/patients/{patient_id}", headers=headers)

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert any(p["gender"] is None for p in list_response.json())
    assert detail_response.json()["gender"] is None


@pytest.mark.asyncio
async def test_medical_record_commit_failure_leaves_no_orphan(
    session_factory: async_sessionmaker[AsyncSession],
    client: AsyncClient,
) -> None:
    """MedicalRecord와 XrayImage를 flush+단일 commit으로 묶은 뒤에는,
    commit이 실패해도 두 INSERT가 함께 롤백되어 고아 행이 남지 않아야 한다."""
    staff = await create_user(session_factory, email="staff-orphan@example.com", role=Role.STAFF)
    token = await login(client, "staff-orphan@example.com")
    patient_resp = await client.post(
        "/api/v1/patients",
        headers=auth_headers(token),
        json={"name": "고아테스트", "age": 33, "gender": "M", "phone": "01011110000"},
    )
    patient_id = patient_resp.json()["id"]

    async with session_factory() as session:
        original_commit = session.commit
        call_count = 0

        async def flaky_commit():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise OperationalError("simulated commit failure", None, None)
            await original_commit()

        session.commit = flaky_commit

        upload = FakeUploadFile(FAKE_JPEG, "image/jpeg")
        with pytest.raises(OperationalError):
            await MedicalRecordService.register(
                session,
                patient_id=patient_id,
                chart_number="ORPHAN-CN-0001",
                symptoms="고아 데이터 테스트",
                xray_image=upload,
                current_user=staff,
            )

    async with session_factory() as session:
        orphan_record = await session.scalar(
            select(MedicalRecord).where(MedicalRecord.chart_number == "ORPHAN-CN-0001")
        )

    # flush + 단일 commit으로 묶었으므로 commit 실패 시 둘 다 롤백되어야 한다.
    assert orphan_record is None, "commit 실패 시 MedicalRecord도 함께 롤백되어야 함"

    # 저장된 파일은 IntegrityError 핸들러에서만 정리되므로, 이 경로(일반 실패)에서는
    # 여전히 남을 수 있다 — 정리만 하고 별도 assert는 하지 않는다.
    for f in (storage.MEDIA_ROOT / storage.XRAY_SUBDIR).glob("*.jpg"):
        f.unlink()


@pytest.mark.asyncio
async def test_patient_delete_survives_file_deletion_failure(
    session_factory: async_sessionmaker[AsyncSession],
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """파일 삭제가 실패해도 DB 삭제가 이미 끝났다면 API는 204를 정상 반환해야 한다
    (파일 삭제 실패는 개별적으로 흡수하고 로깅만 한다)."""
    await create_user(session_factory, email="staff-delfail@example.com", role=Role.STAFF)
    token = await login(client, "staff-delfail@example.com")
    headers = auth_headers(token)

    patient_resp = await client.post(
        "/api/v1/patients",
        headers=headers,
        json={"name": "삭제실패테스트", "age": 44, "gender": "F", "phone": "01022220000"},
    )
    patient_id = patient_resp.json()["id"]

    await client.post(
        "/api/v1/medical-records",
        headers=headers,
        data={
            "patient_id": patient_id,
            "chart_number": "DELFAIL-CN-0001",
            "symptoms": "삭제 실패 테스트",
        },
        files={"xray_image": ("xray.jpg", FAKE_JPEG, "image/jpeg")},
    )

    def raise_on_delete(image_url: str) -> None:
        raise PermissionError("simulated file deletion failure")

    import app.services.patient_service as patient_service_module

    monkeypatch.setattr(patient_service_module, "delete_xray_image", raise_on_delete)

    deleted = await client.delete(f"/api/v1/patients/{patient_id}", headers=headers)
    assert deleted.status_code == 204

    async with session_factory() as session:
        remaining = await session.get(Patient, patient_id)

    assert remaining is None, "파일 삭제 실패와 무관하게 DB 삭제는 성공해야 함"


@pytest.mark.asyncio
async def test_medical_record_integrity_error_survives_file_cleanup_failure(
    session_factory: async_sessionmaker[AsyncSession],
    client: AsyncClient,
) -> None:
    """chart_number 충돌(IntegrityError) 처리 중 파일 삭제 자체가 실패해도,
    원래 의도한 409가 다른 예외로 대체(마스킹)되지 않아야 한다."""
    staff = await create_user(session_factory, email="staff-a1@example.com", role=Role.STAFF)
    token = await login(client, "staff-a1@example.com")
    patient_resp = await client.post(
        "/api/v1/patients",
        headers=auth_headers(token),
        json={"name": "A1테스트", "age": 35, "gender": "M", "phone": "01033330000"},
    )
    patient_id = patient_resp.json()["id"]

    async with session_factory() as session:

        async def failing_commit():
            raise IntegrityError("simulated race-condition duplicate", None, None)

        session.commit = failing_commit

        def raise_os_error(image_url: str) -> None:
            raise OSError("simulated: cannot delete file")

        import app.services.medical_record_service as mrs_module

        original_delete = mrs_module.delete_xray_image
        mrs_module.delete_xray_image = raise_os_error
        try:
            upload = FakeUploadFile(FAKE_JPEG, "image/jpeg")
            with pytest.raises(HTTPException) as exc_info:
                await MedicalRecordService.register(
                    session,
                    patient_id=patient_id,
                    chart_number="A1-CN-0001",
                    symptoms="A1 재현 테스트",
                    xray_image=upload,
                    current_user=staff,
                )
            assert exc_info.value.status_code == 409
        finally:
            mrs_module.delete_xray_image = original_delete


@pytest.mark.asyncio
async def test_medical_record_symptoms_exceeding_byte_limit_rejected(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """symptoms가 MySQL TEXT 한계(65,535바이트)를 넘으면 500이 아니라 422여야 한다."""
    await create_user(session_factory, email="staff-a2@example.com", role=Role.STAFF)
    token = await login(client, "staff-a2@example.com")
    headers = auth_headers(token)

    patient_resp = await client.post(
        "/api/v1/patients",
        headers=headers,
        json={"name": "A2테스트", "age": 36, "gender": "F", "phone": "01044440000"},
    )
    patient_id = patient_resp.json()["id"]

    too_long_symptoms = "가" * 30000  # UTF-8로 약 9만 바이트, 65,535바이트 초과

    response = await client.post(
        "/api/v1/medical-records",
        headers=headers,
        data={
            "patient_id": patient_id,
            "chart_number": "A2-CN-0001",
            "symptoms": too_long_symptoms,
        },
        files={"xray_image": ("xray.jpg", FAKE_JPEG, "image/jpeg")},
    )
    assert response.status_code == 422

    normal_response = await client.post(
        "/api/v1/medical-records",
        headers=headers,
        data={
            "patient_id": patient_id,
            "chart_number": "A2-CN-0002",
            "symptoms": "정상 길이의 증상 텍스트",
        },
        files={"xray_image": ("xray.jpg", FAKE_JPEG, "image/jpeg")},
    )
    assert normal_response.status_code == 201


@pytest.mark.asyncio
async def test_save_xray_image_leaves_no_orphan_on_write_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """save_xray_image가 파일 쓰기 도중 실패해도 고아 파일이 남지 않아야 한다."""
    directory = storage.MEDIA_ROOT / storage.XRAY_SUBDIR
    before = set(directory.glob("*.jpg"))

    def failing_write_bytes(self: Path, data: bytes) -> int:
        self.touch()
        raise OSError("simulated write failure (disk full)")

    monkeypatch.setattr(Path, "write_bytes", failing_write_bytes)

    with pytest.raises(OSError):
        await storage.save_xray_image(FakeUploadFile(FAKE_JPEG, "image/jpeg"))

    after = set(directory.glob("*.jpg"))
    assert after == before, f"고아 파일이 남음: {after - before}"


@pytest.mark.asyncio
async def test_patient_delete_commit_failure_does_not_partially_delete(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """환자 삭제 중 commit이 실패하면 409로 깔끔하게 처리되고,
    환자 데이터가 부분적으로 삭제되지 않아야 한다."""
    async with session_factory() as session:
        patient = Patient(name="B2테스트", age=37, gender=Gender.M, phone="01055550000")
        session.add(patient)
        await session.commit()
        await session.refresh(patient)
        patient_id = patient.id

        async def failing_commit():
            raise IntegrityError("simulated commit failure", None, None)

        session.commit = failing_commit

        with pytest.raises(HTTPException) as exc_info:
            await PatientService.delete(session, patient_id)
        assert exc_info.value.status_code == 409

    async with session_factory() as session:
        remaining = await session.get(Patient, patient_id)
    assert remaining is not None, "commit 실패 시 환자 데이터가 남아있어야 함(부분 삭제 방지)"
