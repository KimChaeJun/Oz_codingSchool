from typing import Annotated

from fastapi import APIRouter, Query, status

from app.apis.dependencies import CurrentStaff, DatabaseSession
from app.schemas.patient import (
    PatientCreateRequest,
    PatientDetailResponse,
    PatientListQuery,
    PatientResponse,
    PatientUpdateRequest,
)
from app.services.patient_service import PatientService

router = APIRouter(prefix="/api/v1/patients", tags=["patients"])


@router.post(
    "",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="환자 정보 등록",
)
async def register_patient(
    body: PatientCreateRequest,
    db: DatabaseSession,
    _staff: CurrentStaff,
):
    return await PatientService.register(db, body)


@router.get(
    "",
    response_model=list[PatientResponse],
    summary="환자 목록 조회",
)
async def list_patients(
    query: Annotated[PatientListQuery, Query()],
    db: DatabaseSession,
    _current_user: CurrentStaff,
):
    return await PatientService.list_patients(db, query)


@router.get(
    "/{patient_id}",
    response_model=PatientDetailResponse,
    summary="환자 정보 상세 조회",
)
async def get_patient(
    patient_id: int,
    db: DatabaseSession,
    _current_user: CurrentStaff,
):
    return await PatientService.get_patient(db, patient_id)


@router.patch(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="환자 정보 수정",
)
async def update_patient(
    patient_id: int,
    body: PatientUpdateRequest,
    db: DatabaseSession,
    _current_user: CurrentStaff,
):
    patient = await PatientService.get_patient(db, patient_id)
    return await PatientService.update(db, patient, body)


@router.delete(
    "/{patient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="환자 정보 삭제",
)
async def delete_patient(
    patient_id: int,
    db: DatabaseSession,
    _current_user: CurrentStaff,
) -> None:
    await PatientService.delete(db, patient_id)
