import asyncio
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy import BigInteger, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import StaticPool

import app.core.storage as storage_module
import app.services.prediction_service as prediction_service_module
import worker.model as worker_model_module
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
from app.repositories.ai_analysis_result_repository import AiAnalysisResultRepository
from app.services.prediction_service import PredictionService

TEST_DATABASE_URL = "sqlite+aiosqlite://"

# 시그니처 바이트(FF D8 FF)는 유효해 save_xray_image 검증은 통과하지만,
# 실제 JPEG 스트림이 아니라 PIL이 디코딩할 수 없는 손상된 이미지.
CORRUPTED_JPEG = b"\xff\xd8\xff\xe0" + b"\x00\x01\x02\x03" * 20


def _make_jpeg_bytes(color: tuple[int, int, int] = (120, 120, 120)) -> bytes:
    """PIL이 실제로 열 수 있는 최소 유효 JPEG. (다른 테스트의 FAKE_JPEG는
    시그니처 바이트만 있어 save_xray_image 검증은 통과하지만 PIL로는 못 연다.)"""
    buffer = BytesIO()
    Image.new("RGB", (64, 64), color=color).save(buffer, format="JPEG")
    return buffer.getvalue()


REAL_JPEG = _make_jpeg_bytes()


# SQLite는 BigInteger PK를 rowid 별칭(autoincrement)으로 인식하지 않는다.
# (tests/test_patient_medical_record_apis.py와 동일한 우회)
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
    department: Department = Department.MEDICAL,
    password: str = "Password1!",
) -> User:
    async with session_factory() as session:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            name="테스트유저",
            department=department,
            gender=Gender.F,
            phone_number=f"010{abs(hash(email)) % 10**8:08d}",
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


async def _create_patient_and_record_with_xray(
    client: AsyncClient, headers: dict, *, chart_number: str
) -> int:
    patient = await client.post(
        "/api/v1/patients",
        headers=headers,
        json={"name": "홍길동", "age": 40, "gender": "M", "phone": "01012345678"},
    )
    patient_id = patient.json()["id"]

    record = await client.post(
        "/api/v1/medical-records",
        headers=headers,
        data={
            "patient_id": patient_id,
            "chart_number": chart_number,
            "symptoms": "기침, 발열",
        },
        files={"xray_image": ("xray.jpg", REAL_JPEG, "image/jpeg")},
    )
    assert record.status_code == 201, record.text
    return record.json()["id"]


@pytest.mark.asyncio
async def test_predict_pneumonia_creates_and_reuses_result(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """1) 정상 POST 예측(실제 ResNet18 모델 사용), 2) 같은 record+model
    재요청 시 재추론 없이 기존 결과 재사용, 8) heatmap_url이 null인지 확인."""
    await create_user(session_factory, email="staff@example.com", role=Role.STAFF)
    token = await login(client, "staff@example.com")
    headers = auth_headers(token)

    record_id = await _create_patient_and_record_with_xray(
        client, headers, chart_number="PRED-CN-0001"
    )

    call_count = 0
    original_predict = prediction_service_module.predict

    def counting_predict(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return original_predict(*args, **kwargs)

    monkeypatch.setattr(prediction_service_module, "predict", counting_predict)

    first = await client.post(
        f"/api/v1/medical-records/{record_id}/predictions", headers=headers
    )
    assert first.status_code == 201, first.text
    body = first.json()
    assert isinstance(body["id"], int)
    assert isinstance(body["is_pneumonia"], bool)
    assert 0.0 <= body["confidence"] <= 100.0
    assert body["heatmap_url"] is None  # 8) 빈 문자열이 null로 변환됐는지
    assert body["record_id"] == record_id
    assert body["model"] == "resnet18_daycon_pure_v1"
    assert "predicted_at" in body
    assert call_count == 1

    second = await client.post(
        f"/api/v1/medical-records/{record_id}/predictions", headers=headers
    )
    assert second.status_code == 200, second.text  # 재사용은 200
    assert second.json()["id"] == body["id"]
    assert second.json() == body
    assert call_count == 1, "기존 결과가 있으면 model.predict가 다시 호출되면 안 됨"


@pytest.mark.asyncio
async def test_predict_pneumonia_missing_record_returns_404(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """3) 존재하지 않는 record_id."""
    await create_user(session_factory, email="staff@example.com", role=Role.STAFF)
    token = await login(client, "staff@example.com")

    response = await client.post(
        "/api/v1/medical-records/999999/predictions",
        headers=auth_headers(token),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_predict_pneumonia_without_xray_returns_409(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """4) X-ray가 없는 진료기록. API로는 X-ray 없이 진료기록을 만들 수
    없으므로(등록 API가 xray_image를 필수로 받음), 세션에 직접 생성한다."""
    await create_user(session_factory, email="staff@example.com", role=Role.STAFF)
    token = await login(client, "staff@example.com")

    async with session_factory() as session:
        patient = Patient(name="X레이없음", age=50, gender=Gender.M, phone="01099990000")
        session.add(patient)
        await session.flush()
        record = MedicalRecord(
            patient_id=patient.id, chart_number="NO-XRAY-0001", symptoms="증상"
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        record_id = record.id

    response = await client.post(
        f"/api/v1/medical-records/{record_id}/predictions",
        headers=auth_headers(token),
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_list_predictions(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """5) GET 목록 조회, 6) 결과 없으면 빈 배열."""
    await create_user(session_factory, email="staff@example.com", role=Role.STAFF)
    token = await login(client, "staff@example.com")
    headers = auth_headers(token)

    record_id = await _create_patient_and_record_with_xray(
        client, headers, chart_number="LIST-CN-0001"
    )

    empty = await client.get(
        f"/api/v1/medical-records/{record_id}/predictions", headers=headers
    )
    assert empty.status_code == 200
    assert empty.json() == []

    created = await client.post(
        f"/api/v1/medical-records/{record_id}/predictions", headers=headers
    )
    assert created.status_code == 201, created.text

    listed = await client.get(
        f"/api/v1/medical-records/{record_id}/predictions", headers=headers
    )
    assert listed.status_code == 200
    items = listed.json()
    assert len(items) == 1
    assert items[0]["id"] == created.json()["id"]
    assert items[0]["heatmap_url"] is None


@pytest.mark.asyncio
async def test_prediction_endpoints_require_staff_or_admin(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """7) 권한 없는 사용자(PENDING)는 거부되어야 한다."""
    await create_user(session_factory, email="staff@example.com", role=Role.STAFF)
    await create_user(session_factory, email="pending@example.com", role=Role.PENDING)

    staff_token = await login(client, "staff@example.com")
    record_id = await _create_patient_and_record_with_xray(
        client, auth_headers(staff_token), chart_number="PERM-CN-0001"
    )

    pending_headers = auth_headers(await login(client, "pending@example.com"))

    denied_post = await client.post(
        f"/api/v1/medical-records/{record_id}/predictions", headers=pending_headers
    )
    assert denied_post.status_code == 403

    denied_get = await client.get(
        f"/api/v1/medical-records/{record_id}/predictions", headers=pending_headers
    )
    assert denied_get.status_code == 403


# =====================================================================
# 1) 인증/권한 경계 (미인증, ADMIN, DEV/RESEARCH 부서)
# =====================================================================


@pytest.mark.asyncio
async def test_predict_requires_authentication(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """Authorization 헤더가 아예 없으면 403이 아니라 401이어야 한다."""
    await create_user(session_factory, email="staff@example.com", role=Role.STAFF)
    staff_headers = auth_headers(await login(client, "staff@example.com"))
    record_id = await _create_patient_and_record_with_xray(
        client, staff_headers, chart_number="AUTH-CN-0001"
    )

    no_auth_post = await client.post(
        f"/api/v1/medical-records/{record_id}/predictions"
    )
    assert no_auth_post.status_code == 401

    no_auth_get = await client.get(
        f"/api/v1/medical-records/{record_id}/predictions"
    )
    assert no_auth_get.status_code == 401


@pytest.mark.asyncio
async def test_predict_allows_admin(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """ADMIN 권한도 허용되어야 한다."""
    await create_user(session_factory, email="admin@example.com", role=Role.ADMIN)
    headers = auth_headers(await login(client, "admin@example.com"))
    record_id = await _create_patient_and_record_with_xray(
        client, headers, chart_number="ADMIN-CN-0001"
    )

    response = await client.post(
        f"/api/v1/medical-records/{record_id}/predictions", headers=headers
    )
    assert response.status_code == 201, response.text


@pytest.mark.asyncio
async def test_predict_allows_dev_and_research_department_staff(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """Day6 URD는 의료인/개발팀/연구자 전체를 허용 대상으로 명시한다.
    CurrentStaff는 Department를 검사하지 않으므로 DEV/RESEARCH 부서
    STAFF도 예측 API에는 허용되어야 한다.

    주의: 진료기록 '등록' API(medical-records POST)는 CurrentMedicalStaff를
    써서 Department==MEDICAL만 허용한다 (Day6 범위 밖, 기존 코드). 그래서
    테스트 데이터 준비는 MEDICAL 부서 계정으로 하고, 예측 API 접근만
    DEV/RESEARCH 계정으로 검증한다.
    """
    await create_user(
        session_factory, email="medical-setup@example.com", role=Role.STAFF
    )
    setup_headers = auth_headers(await login(client, "medical-setup@example.com"))
    record_id = await _create_patient_and_record_with_xray(
        client, setup_headers, chart_number="DEPT-CN-0001"
    )

    await create_user(
        session_factory,
        email="dev@example.com",
        role=Role.STAFF,
        department=Department.DEV,
    )
    dev_headers = auth_headers(await login(client, "dev@example.com"))
    dev_response = await client.post(
        f"/api/v1/medical-records/{record_id}/predictions", headers=dev_headers
    )
    assert dev_response.status_code == 201, dev_response.text

    await create_user(
        session_factory,
        email="research@example.com",
        role=Role.STAFF,
        department=Department.RESEARCH,
    )
    research_headers = auth_headers(await login(client, "research@example.com"))
    research_response = await client.get(
        f"/api/v1/medical-records/{record_id}/predictions", headers=research_headers
    )
    assert research_response.status_code == 200, research_response.text


# =====================================================================
# 2) record/X-ray 오류 (파일 실종, 손상된 이미지)
# =====================================================================


@pytest.mark.asyncio
async def test_predict_xray_file_missing_on_disk_returns_409(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """DB에는 X-ray 레코드가 있지만 실제 파일이 디스크에서 사라진 경우."""
    await create_user(session_factory, email="staff@example.com", role=Role.STAFF)
    headers = auth_headers(await login(client, "staff@example.com"))
    record_id = await _create_patient_and_record_with_xray(
        client, headers, chart_number="MISSING-FILE-CN-0001"
    )

    async with session_factory() as session:
        record = await session.get(
            MedicalRecord, record_id, options=[selectinload(MedicalRecord.xray_images)]
        )
        image_url = record.xray_images[0].image_url

    file_path = storage_module.resolve_media_path(image_url)
    file_path.unlink()  # DB row는 남기고 실제 파일만 지운다

    response = await client.post(
        f"/api/v1/medical-records/{record_id}/predictions", headers=headers
    )
    assert response.status_code == 409
    assert "파일을 찾을 수 없습니다" in response.json()["detail"]


@pytest.mark.asyncio
async def test_predict_corrupted_image_returns_422(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """시그니처 검사는 통과했지만(save_xray_image 통과) 실제로는 PIL이
    디코딩할 수 없는 손상된 이미지 -> 422."""
    await create_user(session_factory, email="staff@example.com", role=Role.STAFF)
    headers = auth_headers(await login(client, "staff@example.com"))

    patient = await client.post(
        "/api/v1/patients",
        headers=headers,
        json={"name": "손상이미지", "age": 45, "gender": "M", "phone": "01033330000"},
    )
    patient_id = patient.json()["id"]
    record = await client.post(
        "/api/v1/medical-records",
        headers=headers,
        data={
            "patient_id": patient_id,
            "chart_number": "CORRUPT-CN-0001",
            "symptoms": "손상 이미지 테스트",
        },
        files={"xray_image": ("xray.jpg", CORRUPTED_JPEG, "image/jpeg")},
    )
    assert record.status_code == 201, record.text
    record_id = record.json()["id"]

    response = await client.post(
        f"/api/v1/medical-records/{record_id}/predictions", headers=headers
    )
    assert response.status_code == 422, response.text


# =====================================================================
# 4) 모델 버전 — MODEL_VERSION 일치 + 다른 버전 결과와의 구분
# =====================================================================


@pytest.mark.asyncio
async def test_predict_uses_current_model_version_and_coexists_with_other_versions(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """저장되는 ai_model이 worker.model.MODEL_VERSION과 정확히 일치하는지,
    다른 model_version의 기존 결과가 있어도 새로 추론해 별개 행으로
    구분되는지 (동시에 10번 '결과가 여러 개면 모두 반환'도 검증)."""
    await create_user(session_factory, email="staff@example.com", role=Role.STAFF)
    headers = auth_headers(await login(client, "staff@example.com"))
    record_id = await _create_patient_and_record_with_xray(
        client, headers, chart_number="VER-CN-0001"
    )

    async with session_factory() as session:
        legacy = AiAnalysisResult(
            record_id=record_id,
            is_pneumonia=False,
            confidence=Decimal("55.00"),
            heatmap_url="",
            ai_model="some_other_model_v0",
        )
        session.add(legacy)
        await session.commit()

    response = await client.post(
        f"/api/v1/medical-records/{record_id}/predictions", headers=headers
    )
    assert response.status_code == 201, response.text  # 캐시 히트가 아니라 새 추론
    assert response.json()["model"] == worker_model_module.MODEL_VERSION

    listed = await client.get(
        f"/api/v1/medical-records/{record_id}/predictions", headers=headers
    )
    assert listed.status_code == 200
    items = listed.json()
    assert len(items) == 2
    assert {item["model"] for item in items} == {
        "some_other_model_v0",
        worker_model_module.MODEL_VERSION,
    }


# =====================================================================
# 5) confidence 계산식
# =====================================================================


@pytest.mark.asyncio
async def test_confidence_calculation_when_pneumonia_positive(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """is_pneumonia=True면 confidence = pneumonia_probability * 100 (소수 둘째자리)."""
    await create_user(session_factory, email="staff@example.com", role=Role.STAFF)
    headers = auth_headers(await login(client, "staff@example.com"))
    record_id = await _create_patient_and_record_with_xray(
        client, headers, chart_number="CONF-POS-CN-0001"
    )

    fixed_prediction = worker_model_module.PneumoniaPrediction(
        is_pneumonia=True, pneumonia_probability=0.82371
    )
    monkeypatch.setattr(
        prediction_service_module, "predict", lambda *_args: fixed_prediction
    )

    response = await client.post(
        f"/api/v1/medical-records/{record_id}/predictions", headers=headers
    )
    assert response.status_code == 201, response.text
    assert response.json()["confidence"] == 82.37


@pytest.mark.asyncio
async def test_confidence_calculation_when_pneumonia_negative(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """is_pneumonia=False면 confidence = (1 - pneumonia_probability) * 100."""
    await create_user(session_factory, email="staff@example.com", role=Role.STAFF)
    headers = auth_headers(await login(client, "staff@example.com"))
    record_id = await _create_patient_and_record_with_xray(
        client, headers, chart_number="CONF-NEG-CN-0001"
    )

    fixed_prediction = worker_model_module.PneumoniaPrediction(
        is_pneumonia=False, pneumonia_probability=0.1237
    )
    monkeypatch.setattr(
        prediction_service_module, "predict", lambda *_args: fixed_prediction
    )

    response = await client.post(
        f"/api/v1/medical-records/{record_id}/predictions", headers=headers
    )
    assert response.status_code == 201, response.text
    assert response.json()["confidence"] == 87.63  # (1 - 0.1237) * 100


# =====================================================================
# 6) label/threshold — API가 worker.model의 판단을 그대로 신뢰하는지
# =====================================================================


@pytest.mark.asyncio
async def test_api_does_not_reapply_threshold(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """API가 worker.model이 반환한 is_pneumonia를 그대로 쓰는지, 자체적으로
    threshold를 재적용하지 않는지 검증한다. probability(0.4, 통상 threshold
    0.5 미만)와 is_pneumonia=True를 일부러 불일치시킨 mock을 줘서, API가
    이 값을 그대로 통과시키는지 확인한다. 만약 API가 자체적으로
    `probability >= 0.5`를 재계산한다면 이 테스트는 False가 반환되어
    실패할 것이다."""
    await create_user(session_factory, email="staff@example.com", role=Role.STAFF)
    headers = auth_headers(await login(client, "staff@example.com"))
    record_id = await _create_patient_and_record_with_xray(
        client, headers, chart_number="THRESH-CN-0001"
    )

    inconsistent_prediction = worker_model_module.PneumoniaPrediction(
        is_pneumonia=True, pneumonia_probability=0.4
    )
    monkeypatch.setattr(
        prediction_service_module, "predict", lambda *_args: inconsistent_prediction
    )

    response = await client.post(
        f"/api/v1/medical-records/{record_id}/predictions", headers=headers
    )
    assert response.status_code == 201, response.text
    assert response.json()["is_pneumonia"] is True
    assert response.json()["confidence"] == 40.0


# =====================================================================
# 8) X-ray 여러 장 — xray_images[0] 사용 여부
# =====================================================================


@pytest.mark.asyncio
async def test_predict_uses_first_xray_image_from_relationship(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """X-ray가 여러 장일 때 실제로 xray_images[0]을 사용하는지 spy로 검증.

    주의: XrayImage relationship에는 order_by가 없어 '어느 게 먼저
    업로드됐는지'는 DB가 보장하지 않는다 (docs/6일차_..md 11장에 명시).
    이 테스트는 '업로드 순서'가 아니라 '코드가 관계에서 반환되는 인덱스
    0을 실제로 쓰는지'만 검증한다 — 즉 기대값도 동일한 방식(인덱스 0)으로
    구한다.
    """
    await create_user(session_factory, email="staff@example.com", role=Role.STAFF)
    headers = auth_headers(await login(client, "staff@example.com"))
    record_id = await _create_patient_and_record_with_xray(
        client, headers, chart_number="MULTI-XRAY-CN-0001"
    )

    async with session_factory() as session:
        second_image = XrayImage(
            record_id=record_id,
            image_url="/media/xray/second-image-does-not-exist.jpg",
            shooting_datetime=datetime.now(UTC),
        )
        session.add(second_image)
        await session.commit()

    captured_paths: list[Path] = []

    def spy_predict(image_path: Path) -> worker_model_module.PneumoniaPrediction:
        captured_paths.append(image_path)
        return worker_model_module.PneumoniaPrediction(
            is_pneumonia=False, pneumonia_probability=0.01
        )

    monkeypatch.setattr(prediction_service_module, "predict", spy_predict)

    response = await client.post(
        f"/api/v1/medical-records/{record_id}/predictions", headers=headers
    )
    assert response.status_code == 201, response.text

    async with session_factory() as session:
        record = await session.get(
            MedicalRecord, record_id, options=[selectinload(MedicalRecord.xray_images)]
        )
        expected_first_image_url = record.xray_images[0].image_url

    assert len(captured_paths) == 1
    assert captured_paths[0] == storage_module.resolve_media_path(
        expected_first_image_url
    )


# =====================================================================
# 9) resolve_media_path 경로 보안 — 순수 유닛 테스트 (HTTP 없음)
# =====================================================================


def test_resolve_media_path_accepts_normal_path() -> None:
    result = storage_module.resolve_media_path("/media/xray/abc123.jpg")
    assert result == (storage_module.MEDIA_ROOT / "xray" / "abc123.jpg").resolve()


def test_resolve_media_path_rejects_non_media_prefix() -> None:
    with pytest.raises(ValueError):
        storage_module.resolve_media_path("/etc/passwd")


def test_resolve_media_path_rejects_traversal_outside_media_root() -> None:
    with pytest.raises(ValueError):
        storage_module.resolve_media_path("/media/../../../../etc/passwd")


def test_resolve_media_path_rejects_symlink_escaping_media_root(
    tmp_path: Path,
) -> None:
    """media/xray/ 안의 심볼릭 링크가 MEDIA_ROOT 밖의 파일을 가리켜도,
    Path.resolve()가 심볼릭 링크를 실제 대상까지 따라가므로 최종 경로가
    거부되어야 한다."""
    outside_target = tmp_path / "secret.txt"
    outside_target.write_text("outside media root")

    directory = storage_module.MEDIA_ROOT / storage_module.XRAY_SUBDIR
    directory.mkdir(parents=True, exist_ok=True)
    symlink_path = directory / "evil_symlink.jpg"
    if symlink_path.is_symlink() or symlink_path.exists():
        symlink_path.unlink()
    symlink_path.symlink_to(outside_target)

    try:
        with pytest.raises(ValueError):
            storage_module.resolve_media_path(
                f"/media/{storage_module.XRAY_SUBDIR}/evil_symlink.jpg"
            )
    finally:
        symlink_path.unlink(missing_ok=True)


# =====================================================================
# 10) GET 목록 — 응답 필드가 설계와 정확히 일치하는지
# =====================================================================


@pytest.mark.asyncio
async def test_prediction_response_fields_exactly_match_design(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """응답 필드가 팀장님 설계 문서(app/schemas/prediction.py, chaejun_sub1)
    기준 필드명과 정확히 일치하는지. record_id/predicted_at/model이
    팀 공통 응답 규격이므로, 이 필드들이 정확히 존재해야 한다."""
    await create_user(session_factory, email="staff@example.com", role=Role.STAFF)
    headers = auth_headers(await login(client, "staff@example.com"))
    record_id = await _create_patient_and_record_with_xray(
        client, headers, chart_number="FIELDS-CN-0001"
    )

    created = await client.post(
        f"/api/v1/medical-records/{record_id}/predictions", headers=headers
    )
    assert created.status_code == 201, created.text
    expected_fields = {
        "id",
        "record_id",
        "is_pneumonia",
        "confidence",
        "heatmap_url",
        "predicted_at",
        "model",
    }
    assert set(created.json().keys()) == expected_fields
    assert created.json()["record_id"] == record_id

    listed = await client.get(
        f"/api/v1/medical-records/{record_id}/predictions", headers=headers
    )
    assert listed.status_code == 200
    assert set(listed.json()[0].keys()) == expected_fields


# =====================================================================
# 11) DB 저장/트랜잭션
# =====================================================================


@pytest.mark.asyncio
async def test_predict_result_is_actually_persisted_in_db(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """API 응답만 보지 않고, 완전히 별도의 세션으로 DB에 실제 저장됐는지
    직접 확인한다."""
    await create_user(session_factory, email="staff@example.com", role=Role.STAFF)
    headers = auth_headers(await login(client, "staff@example.com"))
    record_id = await _create_patient_and_record_with_xray(
        client, headers, chart_number="PERSIST-CN-0001"
    )

    response = await client.post(
        f"/api/v1/medical-records/{record_id}/predictions", headers=headers
    )
    assert response.status_code == 201, response.text
    result_id = response.json()["id"]

    async with session_factory() as session:
        stored = await session.get(AiAnalysisResult, result_id)
        assert stored is not None
        assert stored.record_id == record_id
        assert stored.is_pneumonia == response.json()["is_pneumonia"]
        assert stored.ai_model == worker_model_module.MODEL_VERSION
        assert stored.heatmap_url == ""  # DB에는 빈 문자열 그대로 저장됨


@pytest.mark.asyncio
async def test_predict_commit_failure_does_not_leave_orphan_or_corrupt_session(
    session_factory: async_sessionmaker[AsyncSession],
    client: AsyncClient,
) -> None:
    """commit이 실패해도 (a) 결과가 저장되지 않고 (b) 이후 요청(새 세션)에
    영향을 주지 않아야 한다. production code는 수정하지 않는다 —
    prediction_service.py는 commit 실패를 별도로 catch하지 않으므로,
    예외가 그대로 전파되는 것이 현재 구현의 실제 동작이다."""
    await create_user(session_factory, email="staff@example.com", role=Role.STAFF)
    headers = auth_headers(await login(client, "staff@example.com"))
    record_id = await _create_patient_and_record_with_xray(
        client, headers, chart_number="COMMIT-FAIL-CN-0001"
    )

    async with session_factory() as session:

        async def failing_commit() -> None:
            raise OperationalError("simulated commit failure", None, None)

        session.commit = failing_commit

        with pytest.raises(OperationalError):
            await PredictionService.predict(session, record_id)

    # (a) 완전히 새 세션으로 확인 — 저장된 결과가 없어야 한다
    async with session_factory() as fresh_session:
        stored = await AiAnalysisResultRepository.get_by_record_and_model(
            fresh_session,
            record_id=record_id,
            ai_model=worker_model_module.MODEL_VERSION,
        )
        assert stored is None, "commit 실패 시 결과가 저장되면 안 됨"

    # (b) 세션 오염 여부 — HTTP 레이어는 요청마다 새 세션을 쓰므로,
    # 같은 record로 다시 시도해도 정상 동작해야 한다
    retry = await client.post(
        f"/api/v1/medical-records/{record_id}/predictions", headers=headers
    )
    assert retry.status_code == 201, retry.text


# =====================================================================
# 12) 동시 요청 경쟁 상태 — 알려진 설계상 한계의 재현 시도
# =====================================================================


@pytest.mark.asyncio
async def test_concurrent_predict_requests_may_create_duplicate_rows(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """알려진 설계상 한계: record_id+ai_model에 DB UniqueConstraint가 없으므로
    동시 요청이 겹치면 중복 행이 생길 수 있다 (docs/6일차_..md 4.4/11장,
    prediction_service.py 주석 참고). 이 테스트는 '올바른 동작(중복 없음)'을
    기준으로 assert했다 — 재현되면 이 테스트는 의도적으로 FAIL한 채로 남는다.
    이 문제를 해결하기 위해 production code나 migration을 추가하지 않는다."""
    await create_user(session_factory, email="staff@example.com", role=Role.STAFF)
    headers = auth_headers(await login(client, "staff@example.com"))
    record_id = await _create_patient_and_record_with_xray(
        client, headers, chart_number="RACE-CN-0001"
    )

    def slow_predict(image_path: Path) -> worker_model_module.PneumoniaPrediction:
        time.sleep(0.05)  # 두 요청의 "체크 후 삽입" 구간을 넓혀 경쟁을 유도
        return worker_model_module.PneumoniaPrediction(
            is_pneumonia=False, pneumonia_probability=0.01
        )

    monkeypatch.setattr(prediction_service_module, "predict", slow_predict)

    responses = await asyncio.gather(
        client.post(f"/api/v1/medical-records/{record_id}/predictions", headers=headers),
        client.post(f"/api/v1/medical-records/{record_id}/predictions", headers=headers),
    )
    for response in responses:
        assert response.status_code in (200, 201), response.text

    async with session_factory() as session:
        rows = (
            await session.scalars(
                select(AiAnalysisResult).where(
                    AiAnalysisResult.record_id == record_id
                )
            )
        ).all()

    assert len(rows) == 1, (
        f"UniqueConstraint가 없어 동시 요청 시 중복 행이 생겼습니다 "
        f"(실제 {len(rows)}개). 알려진 설계상 한계이며, 이 테스트 실패는 "
        "production code 버그 수정 대상이 아니라 의도적으로 남겨둔 한계의 "
        "재현입니다 — docs/6일차_폐렴예측_API_설계.md 4.4/11장 참고."
    )


# =====================================================================
# 13) NFR-PRED-002 — 실제 추론 시간 및 모델 캐싱
# =====================================================================


def test_model_inference_performance_and_caching() -> None:
    """실제 추론 시간이 3초 이내인지, 모델이 캐싱되어 재사용되는지 측정한다.
    load_model.cache_clear()로 강제로 콜드 스타트를 만들어 '모델 로딩을
    포함한 첫 호출'과 '이미 로드된 상태의 두 번째 호출'을 구분해서 측정한다.
    """
    worker_model_module.load_model.cache_clear()

    buffer = BytesIO()
    Image.new("RGB", (64, 64), color=(80, 80, 80)).save(buffer, format="JPEG")

    buffer.seek(0)
    start = time.perf_counter()
    worker_model_module.predict(buffer)
    first_call_seconds = time.perf_counter() - start

    buffer.seek(0)
    start = time.perf_counter()
    worker_model_module.predict(buffer)
    second_call_seconds = time.perf_counter() - start

    assert first_call_seconds < 3.0, (
        f"NFR-PRED-002(3초 이내) 위반 가능성: 첫 추론 {first_call_seconds:.3f}s"
    )
    assert second_call_seconds < 3.0, (
        f"NFR-PRED-002(3초 이내) 위반 가능성: 두 번째 추론 {second_call_seconds:.3f}s"
    )

    # 모델 인스턴스가 재사용되는지 (요청마다 재로딩되지 않는지)
    assert worker_model_module.load_model() is worker_model_module.load_model()

    print(
        f"\n[성능] 첫 추론(모델 로딩 포함): {first_call_seconds:.3f}s, "
        f"두 번째 추론(캐시됨): {second_call_seconds:.3f}s"
    )


# =====================================================================
# Day7 프론트 연결 전 최종 점검 — record 간 격리, POST/GET 일관성
# =====================================================================


@pytest.mark.asyncio
async def test_get_predictions_does_not_leak_across_records(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """서로 다른 진료기록(record A, record B)에 각각 예측을 저장했을 때,
    GET이 자기 record의 결과만 반환하고 다른 record의 결과가 섞이지
    않는지 검증한다. 지난 감사에서 발견한 커버리지 공백."""
    await create_user(session_factory, email="staff@example.com", role=Role.STAFF)
    headers = auth_headers(await login(client, "staff@example.com"))

    record_a_id = await _create_patient_and_record_with_xray(
        client, headers, chart_number="ISOLATE-A-CN-0001"
    )
    record_b_id = await _create_patient_and_record_with_xray(
        client, headers, chart_number="ISOLATE-B-CN-0001"
    )
    assert record_a_id != record_b_id

    post_a = await client.post(
        f"/api/v1/medical-records/{record_a_id}/predictions", headers=headers
    )
    assert post_a.status_code == 201, post_a.text

    post_b = await client.post(
        f"/api/v1/medical-records/{record_b_id}/predictions", headers=headers
    )
    assert post_b.status_code == 201, post_b.text

    assert post_a.json()["id"] != post_b.json()["id"]

    list_a = await client.get(
        f"/api/v1/medical-records/{record_a_id}/predictions", headers=headers
    )
    assert list_a.status_code == 200
    items_a = list_a.json()
    assert len(items_a) == 1
    assert items_a[0]["id"] == post_a.json()["id"]
    assert items_a[0]["id"] != post_b.json()["id"]

    list_b = await client.get(
        f"/api/v1/medical-records/{record_b_id}/predictions", headers=headers
    )
    assert list_b.status_code == 200
    items_b = list_b.json()
    assert len(items_b) == 1
    assert items_b[0]["id"] == post_b.json()["id"]
    assert items_b[0]["id"] != post_a.json()["id"]


@pytest.mark.asyncio
async def test_post_response_and_get_response_are_consistent(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """POST로 생성/반환된 결과의 7개 핵심 필드(id, record_id, is_pneumonia,
    confidence, heatmap_url, predicted_at, model — 팀장님 설계 문서 기준
    필드명)가 이후 같은 결과를 GET 목록에서 조회했을 때와 완전히 동일한지
    검증한다. 프론트가 POST 응답을 즉시 화면에 쓰든, 나중에 GET으로 다시
    불러와 쓰든 데이터 의미가 같아야 Day7에서 두 경로를 섞어 써도 안전하다."""
    await create_user(session_factory, email="staff@example.com", role=Role.STAFF)
    headers = auth_headers(await login(client, "staff@example.com"))
    record_id = await _create_patient_and_record_with_xray(
        client, headers, chart_number="CONSISTENCY-CN-0001"
    )

    post_response = await client.post(
        f"/api/v1/medical-records/{record_id}/predictions", headers=headers
    )
    assert post_response.status_code == 201, post_response.text
    post_body = post_response.json()

    core_fields = {
        "id",
        "record_id",
        "is_pneumonia",
        "confidence",
        "heatmap_url",
        "predicted_at",
        "model",
    }
    assert set(post_body.keys()) == core_fields

    list_response = await client.get(
        f"/api/v1/medical-records/{record_id}/predictions", headers=headers
    )
    assert list_response.status_code == 200
    matching = [item for item in list_response.json() if item["id"] == post_body["id"]]
    assert len(matching) == 1, "POST가 만든 결과가 GET 목록에 정확히 하나 나와야 함"
    get_body = matching[0]

    for field in core_fields:
        assert get_body[field] == post_body[field], (
            f"필드 '{field}' 불일치: POST={post_body[field]!r} GET={get_body[field]!r}"
        )
