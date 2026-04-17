from fastapi import APIRouter, Depends, HTTPException

from depression_detection.interfaces.api.deps import get_reading_service
from depression_detection.model.schemas import PredictionResult
from depression_detection.tasks.reading.schemas import ReadingRequest
from depression_detection.shared.exceptions import FeatureNotReadyError

router = APIRouter(prefix="/api/v1", tags=["reading"])


@router.post("/reading:predict", response_model=PredictionResult)
def predict_reading(request: ReadingRequest, service=Depends(get_reading_service)):
    try:
        return service.predict(request.sample_id, request.audio_path, request.transcript)
    except FeatureNotReadyError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
