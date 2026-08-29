from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.apis.dependencies import DatabaseSession
from app.models import MedicalRecord, Patient, XrayImage
from app.models.user import Gender
from app.schemas.patient import (
    MedicalRecordListItemResponse,
    MedicalRecordListItemsResponse,
    MedicalRecordResponse,
    MedicalRecordUpdate,
    PatientCreate,
    PatientListResponse,
    PatientResponse,
    PatientUpdate,
)

router = APIRouter(prefix="/api/v1", tags=["patients"])
UPLOAD_DIR = Path("uploads")
MAX_FILE_SIZE = 10 * 1024 * 1024


async def _patient_or_404(db: DatabaseSession, patient_id: int) -> Patient:
    patient = await db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="환자를 찾을 수 없습니다.")
    return patient


async def _record_or_404(db: DatabaseSession, record_id: int) -> MedicalRecord:
    result = await db.execute(
        select(MedicalRecord)
        .options(selectinload(MedicalRecord.xray_images))
        .where(MedicalRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="진료기록을 찾을 수 없습니다.")
    return record


@router.post("/patients", response_model=PatientResponse, status_code=201)
async def create_patient(body: PatientCreate, db: DatabaseSession):
    if await db.scalar(select(Patient).where(Patient.phone == body.phone)):
        raise HTTPException(status_code=409, detail="중복된 연락처입니다.")
    patient = Patient(**body.model_dump())
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient


@router.get("/patients", response_model=PatientListResponse)
async def get_patients(
    db: DatabaseSession,
    name: str | None = None,
    gender: Gender | None = None,
    min_age: int | None = Query(default=None, ge=0, le=150),
    max_age: int | None = Query(default=None, ge=0, le=150),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
):
    filters = []
    if name:
        filters.append(Patient.name.contains(name))
    if gender:
        filters.append(Patient.gender == gender)
    if min_age is not None:
        filters.append(Patient.age >= min_age)
    if max_age is not None:
        filters.append(Patient.age <= max_age)
    total = await db.scalar(select(func.count(Patient.id)).where(*filters))
    result = await db.execute(
        select(Patient).where(*filters).order_by(Patient.id)
        .offset((page - 1) * size).limit(size)
    )
    return {"items": list(result.scalars()), "total": total or 0, "page": page, "size": size}


@router.get("/patients/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: int, db: DatabaseSession):
    return await _patient_or_404(db, patient_id)


@router.patch("/patients/{patient_id}", response_model=PatientResponse)
async def update_patient(patient_id: int, body: PatientUpdate, db: DatabaseSession):
    patient = await _patient_or_404(db, patient_id)
    values = body.model_dump(exclude_unset=True)
    if values.get("phone") and values["phone"] != patient.phone:
        duplicate = await db.scalar(select(Patient).where(Patient.phone == values["phone"]))
        if duplicate:
            raise HTTPException(status_code=409, detail="중복된 연락처입니다.")
    for key, value in values.items():
        setattr(patient, key, value)
    await db.commit()
    await db.refresh(patient)
    return patient


@router.delete("/patients/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(patient_id: int, db: DatabaseSession):
    patient = await _patient_or_404(db, patient_id)
    await db.delete(patient)
    await db.commit()


@router.post("/patients/{patient_id}/medical-records", response_model=MedicalRecordResponse, status_code=201)
async def create_medical_record(
    patient_id: int,
    db: DatabaseSession,
    chart_number: str = Form(min_length=1, max_length=50),
    symptoms: str = Form(min_length=1, max_length=1000),
    xray_images: list[UploadFile] = File(min_length=1),
):
    await _patient_or_404(db, patient_id)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    record = MedicalRecord(patient_id=patient_id, chart_number=chart_number, symptoms=symptoms)
    db.add(record)
    saved_paths: list[Path] = []
    try:
        await db.flush()
        for upload in xray_images:
            content = await upload.read(MAX_FILE_SIZE + 1)
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail="파일 크기가 10MB를 초과합니다.")
            filename = f"{patient_id}_{record.id}_{uuid4().hex}{Path(upload.filename or 'xray').suffix}"
            path = UPLOAD_DIR / filename
            path.write_bytes(content)
            saved_paths.append(path)
            db.add(XrayImage(record_id=record.id, uploader_id=None,
                             image_url=f"uploads/{filename}", shooting_datetime=datetime.utcnow()))
        await db.commit()
    except (HTTPException, IntegrityError):
        await db.rollback()
        for path in saved_paths:
            path.unlink(missing_ok=True)
        raise
    return await _record_or_404(db, record.id)


@router.get("/patients/{patient_id}/medical-records", response_model=MedicalRecordListItemsResponse)
async def get_medical_records(patient_id: int, db: DatabaseSession):
    await _patient_or_404(db, patient_id)
    result = await db.execute(
        select(MedicalRecord).where(MedicalRecord.patient_id == patient_id).order_by(MedicalRecord.id)
    )
    records = list(result.scalars())
    items = [MedicalRecordListItemResponse(
        id=record.id, patient_id=record.patient_id, chart_number=record.chart_number,
        symptoms=record.symptoms[:100] + ("..." if len(record.symptoms) > 100 else ""),
        created_at=record.created_at,
    ) for record in records]
    return {"items": items, "total": len(items)}


@router.get("/medical-records/{record_id}", response_model=MedicalRecordResponse)
async def get_medical_record(record_id: int, db: DatabaseSession):
    return await _record_or_404(db, record_id)


@router.patch("/medical-records/{record_id}", response_model=MedicalRecordResponse)
async def update_medical_record(record_id: int, body: MedicalRecordUpdate, db: DatabaseSession):
    record = await _record_or_404(db, record_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    await db.commit()
    return await _record_or_404(db, record_id)


@router.delete("/medical-records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medical_record(record_id: int, db: DatabaseSession):
    record = await _record_or_404(db, record_id)
    paths = [Path(image.image_url) for image in record.xray_images]
    await db.delete(record)
    await db.commit()
    for path in paths:
        path.unlink(missing_ok=True)
