from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.models.user import User

from app.apis.dependencies import get_current_user
from app.models.patient import Patient
from app.schemas.patient import (
    PatientCreate,
    PatientListQuery,
    PatientListResponse,
    PatientResponse,
    PatientUpdate,
)

router = APIRouter(
    prefix="/api/v1/patients",
    tags=["patients"],
)


@router.post(
    "",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="환자 정보 등록",
)
async def create_patient(
    body: PatientCreate,
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    patient = Patient(
        name=body.name,
        age=body.age,
        gender=body.gender,
        phone=body.phone,
    )

    db.add(patient)
    await db.commit()
    await db.refresh(patient)

    return patient


@router.get(
    "",
    response_model=PatientListResponse,
    summary="환자 목록 조회",
)
async def get_patients(
    query: Annotated[PatientListQuery, Query()],
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    stmt = select(Patient)
    count_stmt = select(func.count()).select_from(Patient)

    if query.name:
        name_filter = Patient.name.contains(query.name)
        stmt = stmt.where(name_filter)
        count_stmt = count_stmt.where(name_filter)

    if query.gender:
        stmt = stmt.where(Patient.gender == query.gender)
        count_stmt = count_stmt.where(Patient.gender == query.gender)

    if query.min_age is not None:
        stmt = stmt.where(Patient.age >= query.min_age)
        count_stmt = count_stmt.where(Patient.age >= query.min_age)

    if query.max_age is not None:
        stmt = stmt.where(Patient.age <= query.max_age)
        count_stmt = count_stmt.where(Patient.age <= query.max_age)

    total = await db.scalar(count_stmt)

    result = await db.execute(
        stmt.order_by(Patient.id.desc())
        .offset((query.page - 1) * query.size)
        .limit(query.size)
    )

    return PatientListResponse(
        items=result.scalars().all(),
        total=total or 0,
        page=query.page,
        size=query.size,
    )


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="환자 정보 상세 조회",
)
async def get_patient(
    patient_id: int,
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    patient = await db.get(Patient, patient_id)

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="환자를 찾을 수 없습니다.",
        )

    return patient


@router.patch(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="환자 정보 수정",
)
async def update_patient(
    patient_id: int,
    body: PatientUpdate,
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    patient = await db.get(Patient, patient_id)

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="환자를 찾을 수 없습니다.",
        )

    if body.name is not None:
        patient.name = body.name

    if body.phone is not None:
        patient.phone = body.phone

    await db.commit()
    await db.refresh(patient)

    return patient


@router.delete(
    "/{patient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="환자 정보 삭제",
)
async def delete_patient(
    patient_id: int,
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    patient = await db.get(Patient, patient_id)

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="환자를 찾을 수 없습니다.",
        )

    await db.delete(patient)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)