from typing import Annotated

from fastapi import APIRouter, Path, Response, status

from app.apis.dependencies import CurrentStaff, DatabaseSession
from app.schemas.prediction import PredictionResponse, PredictionRunResponse
from app.services.prediction_service import PredictionService

router = APIRouter(
    prefix="/api/v1/medical-records/{record_id}/predictions",
    tags=["predictions"],
)


@router.post(
    "",
    response_model=PredictionRunResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_200_OK: {
            "model": PredictionRunResponse,
            "description": "동일 모델의 저장된 예측 결과 재사용",
        }
    },
    summary="폐렴 예측 실행",
)
async def predict_pneumonia(
    record_id: Annotated[int, Path(gt=0)],
    response: Response,
    db: DatabaseSession,
    _current_user: CurrentStaff,
) -> PredictionRunResponse:
    execution = await PredictionService.predict(db, record_id)
    if execution.cached:
        response.status_code = status.HTTP_200_OK

    prediction = PredictionResponse.model_validate(execution.result)
    return PredictionRunResponse(
        **prediction.model_dump(),
        cached=execution.cached,
    )


@router.get(
    "",
    response_model=list[PredictionResponse],
    summary="폐렴 예측 결과 목록 조회",
)
async def list_pneumonia_predictions(
    record_id: Annotated[int, Path(gt=0)],
    db: DatabaseSession,
    _current_user: CurrentStaff,
) -> list[PredictionResponse]:
    results = await PredictionService.list_by_record(db, record_id)
    return [PredictionResponse.model_validate(result) for result in results]
