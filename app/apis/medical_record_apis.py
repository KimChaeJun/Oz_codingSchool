from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.apis.dependencies import get_current_user
from app.core.db.databases import async_get_db
from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.models.user import Department, User
from app.models.xray_image import XrayImage
from app.schemas.medical_record import (
    MedicalRecordListItem,
    MedicalRecordListResponse,
    MedicalRecordResponse,
    MedicalRecordUpdate,
)


router = APIRouter(
    prefix="/api/v1/patients/{patient_id}/medical-records",
    tags=["medical-records"],
)


MAX_XRAY_SIZE = 10 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png"}


def get_media_directory() -> Path:
    directory = Path(__file__).resolve().parents[2] / "media" / "xray"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_media_path(image_url: str) -> Path | None:
    prefix = "/media/xray/"

    if not image_url.startswith(prefix):
        return None

    filename = Path(image_url.removeprefix(prefix)).name
    image_path = get_media_directory() / filename

    if image_path.parent != get_media_directory():
        return None

    return image_path


def require_medical_staff(current_user: User) -> None:
    if current_user.department != Department.MEDICAL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="의료진 권한이 필요합니다.",
        )


async def get_patient(
    patient_id: int,
    db: AsyncSession,
) -> Patient:
    patient = await db.get(Patient, patient_id)

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="환자를 찾을 수 없습니다.",
        )

    return patient


async def validate_xray_image(
    xray_image: UploadFile,
) -> tuple[bytes, str]:
    content_type = xray_image.content_type or ""

    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="JPG 또는 PNG 이미지만 업로드할 수 있습니다.",
        )

    image_data = await xray_image.read(MAX_XRAY_SIZE + 1)

    if len(image_data) > MAX_XRAY_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="이미지 파일은 10MB 이하만 업로드할 수 있습니다.",
        )

    if content_type == "image/jpeg":
        is_valid_image = image_data.startswith(b"\xff\xd8\xff")
        suffix = ".jpg"
    else:
        is_valid_image = image_data.startswith(
            b"\x89PNG\r\n\x1a\n"
        )
        suffix = ".png"

    if not is_valid_image:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="파일 내용이 이미지 형식과 일치하지 않습니다.",
        )

    return image_data, suffix


async def get_record(
    patient_id: int,
    record_id: int,
    db: AsyncSession,
) -> MedicalRecord:
    result = await db.execute(
        select(MedicalRecord)
        .options(selectinload(MedicalRecord.xray_images))
        .where(
            MedicalRecord.id == record_id,
            MedicalRecord.patient_id == patient_id,
        )
    )

    record = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="진료기록을 찾을 수 없습니다.",
        )

    return record


@router.post(
    "",
    response_model=MedicalRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="진료기록 등록",
)
async def create_medical_record(
    patient_id: int,
    chart_number: str = Form(...),
    symptoms: str = Form(...),
    xray_image: UploadFile = File(...),
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user),
):
    require_medical_staff(current_user)
    await get_patient(patient_id, db)

    image_data, suffix = await validate_xray_image(xray_image)

    record = MedicalRecord(
        patient_id=patient_id,
        chart_number=chart_number,
        symptoms=symptoms,
    )

    db.add(record)
    await db.flush()

    filename = f"{uuid4().hex}{suffix}"
    file_path = get_media_directory() / filename

    try:
        file_path.write_bytes(image_data)
    except OSError as exc:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 파일 저장에 실패했습니다.",
        ) from exc

    image = XrayImage(
        record_id=record.id,
        uploader_id=current_user.id,
        image_url=f"/media/xray/{filename}",
        shooting_datetime=datetime.now(),
    )

    db.add(image)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        file_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 차트 번호입니다.",
        ) from exc
    except Exception as exc:
        await db.rollback()
        file_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="진료기록 저장에 실패했습니다.",
        ) from exc

    return await get_record(patient_id, record.id, db)


@router.get(
    "",
    response_model=MedicalRecordListResponse,
    summary="진료기록 목록 조회",
)
async def get_medical_records(
    patient_id: int,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user),
):
    await get_patient(patient_id, db)

    base_condition = MedicalRecord.patient_id == patient_id

    count_stmt = select(func.count()).select_from(
        MedicalRecord
    ).where(base_condition)

    total = await db.scalar(count_stmt)

    result = await db.execute(
        select(MedicalRecord)
        .where(base_condition)
        .order_by(MedicalRecord.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )

    records = result.scalars().all()

    items = [
        MedicalRecordListItem(
            id=record.id,
            patient_id=record.patient_id,
            chart_number=record.chart_number,
            symptoms=(
                record.symptoms[:100] + "..."
                if len(record.symptoms) > 100
                else record.symptoms
            ),
            created_at=record.created_at,
        )
        for record in records
    ]

    return MedicalRecordListResponse(
        items=items,
        total=total or 0,
    )


@router.get(
    "/{record_id}",
    response_model=MedicalRecordResponse,
    summary="진료기록 상세 조회",
)
async def get_medical_record(
    patient_id: int,
    record_id: int,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_record(patient_id, record_id, db)


@router.patch(
    "/{record_id}",
    response_model=MedicalRecordResponse,
    summary="진료기록 수정",
)
async def update_medical_record(
    patient_id: int,
    record_id: int,
    body: MedicalRecordUpdate,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user),
):
    record = await get_record(patient_id, record_id, db)

    if body.symptoms is not None:
        record.symptoms = body.symptoms

    await db.commit()

    return await get_record(patient_id, record_id, db)


@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="진료기록 삭제",
)
async def delete_medical_record(
    patient_id: int,
    record_id: int,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user),
):
    record = await get_record(patient_id, record_id, db)

    image_paths = [
        image_path
        for image in record.xray_images
        if (image_path := get_media_path(image.image_url)) is not None
    ]

    await db.delete(record)
    await db.commit()

    for image_path in image_paths:
        image_path.unlink(missing_ok=True)

    return Response(status_code=status.HTTP_204_NO_CONTENT)