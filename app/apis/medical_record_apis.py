from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status

from app.apis.dependencies import CurrentStaff, DatabaseSession
from app.schemas.medical_record import (
    MedicalRecordDetailResponse,
    MedicalRecordListItemResponse,
)
from app.services.medical_record_service import MedicalRecordService

router = APIRouter(prefix="/api/v1", tags=["medical-records"])


@router.post(
    "/medical-records",
    response_model=MedicalRecordDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="진료기록 등록",
)
async def register_medical_record(
    db: DatabaseSession,
    current_user: CurrentStaff,
    patient_id: Annotated[int, Form()],
    chart_number: Annotated[str, Form(min_length=1, max_length=50)],
    symptoms: Annotated[str, Form(min_length=1)],
    xray_image: Annotated[UploadFile, File()],
):
    return await MedicalRecordService.register(
        db,
        patient_id=patient_id,
        chart_number=chart_number,
        symptoms=symptoms,
        xray_image=xray_image,
        current_user=current_user,
    )


@router.get(
    "/patients/{patient_id}/medical-records",
    response_model=list[MedicalRecordListItemResponse],
    summary="환자 진료기록 목록 조회",
)
async def list_patient_medical_records(
    patient_id: int,
    db: DatabaseSession,
    _current_user: CurrentStaff,
):
    return await MedicalRecordService.list_by_patient(db, patient_id)


@router.get(
    "/medical-records/{record_id}",
    response_model=MedicalRecordDetailResponse,
    summary="진료기록 상세 조회",
)
async def get_medical_record(
    record_id: int,
    db: DatabaseSession,
    _current_user: CurrentStaff,
):
    return await MedicalRecordService.get_detail(db, record_id)
