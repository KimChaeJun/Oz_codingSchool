from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db.databases import async_get_db
from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.models.user import User
from app.models.xray_image import XrayImage
from app.schemas.medical_record import (
    MedicalRecordListItem,
    MedicalRecordListResponse,
    MedicalRecordResponse,
    MedicalRecordUpdate,
)
from app.apis.dependencies import get_current_user

router = APIRouter(
    prefix="/api/v1/patients/{patient_id}/medical-records",
    tags=["medical-records"],
)


def get_media_directory() -> Path:
    directory = Path(__file__).resolve().parents[2] / "media" / "xray"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


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

    patient = await db.get(Patient, patient_id)

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="환자를 찾을 수 없습니다.",
        )

    if (
        not xray_image.content_type
        or not xray_image.content_type.startswith("image/")
    ):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="이미지 파일만 업로드할 수 있습니다.",
        )

    record = MedicalRecord(
        patient_id=patient_id,
        chart_number=chart_number,
        symptoms=symptoms,
    )

    db.add(record)
    await db.flush()

    suffix = Path(xray_image.filename or "").suffix.lower()
    filename = f"{uuid4().hex}{suffix}"
    file_path = get_media_directory() / filename

    file_path.write_bytes(await xray_image.read())

    image = XrayImage(
        record_id=record.id,
        uploader_id=current_user.id,
        image_url=f"/media/xray/{filename}",
        shooting_datetime=datetime.now(),
    )

    db.add(image)
    await db.commit()

    result = await db.execute(
        select(MedicalRecord)
        .options(selectinload(MedicalRecord.xray_images))
        .where(MedicalRecord.id == record.id)
    )

    return result.scalar_one()


@router.get(
    "",
    response_model=MedicalRecordListResponse,
    summary="진료기록 목록 조회",
)
async def get_medical_records(
    patient_id: int,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user),
):
    patient = await db.get(Patient, patient_id)

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="환자를 찾을 수 없습니다.",
        )

    count_stmt = select(func.count()).select_from(MedicalRecord).where(
        MedicalRecord.patient_id == patient_id
    )

    total = await db.scalar(count_stmt)

    result = await db.execute(
        select(MedicalRecord)
        .where(MedicalRecord.patient_id == patient_id)
        .order_by(MedicalRecord.id.desc())
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

    await db.delete(record)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)