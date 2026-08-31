from fastapi import APIRouter, Response, status

from app.apis.dependencies import CurrentStaff, DatabaseSession
from app.schemas.prediction import PredictionResponse
from app.services.prediction_service import PredictionService

router = APIRouter(
    prefix="/api/v1/medical-records/{record_id}/predictions",
    tags=["predictions"],
)


@router.post(
    "",
    response_model=PredictionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_200_OK: {
            "model": PredictionResponse,
            "description": "동일 모델의 기존 예측 결과를 재사용함",
        }
    },
    summary="폐렴 예측 실행",
)
async def predict_pneumonia(
    record_id: int,
    response: Response,
    db: DatabaseSession,
    _current_user: CurrentStaff,
) -> PredictionResponse:
    result, cached = await PredictionService.predict(db, record_id)
    if cached:
        response.status_code = status.HTTP_200_OK
    return PredictionResponse.model_validate(result)


@router.get(
    "",
    response_model=list[PredictionResponse],
    summary="폐렴 예측 결과 목록 조회",
)
async def list_pneumonia_predictions(
    record_id: int,
    db: DatabaseSession,
    _current_user: CurrentStaff,
) -> list[PredictionResponse]:
    results = await PredictionService.list_by_record(db, record_id)
    return [PredictionResponse.model_validate(result) for result in results]
