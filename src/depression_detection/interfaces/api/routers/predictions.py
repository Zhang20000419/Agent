from fastapi import APIRouter, Depends, HTTPException

from depression_detection.interfaces.api.deps import get_prediction_service
from depression_detection.model.schemas import (
    AudioPredictionInput,
    MultimodalPredictionInput,
    PredictionResult,
    TextPredictionInput,
    VisionPredictionInput,
)
from depression_detection.shared.exceptions import FeatureNotReadyError

router = APIRouter(prefix="/api/v1", tags=["prediction"])


@router.post("/text:predict", response_model=PredictionResult)
def predict_text(request: TextPredictionInput, service=Depends(get_prediction_service)):
    try:
        return service.predict_text(request)
    except FeatureNotReadyError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc


@router.post("/audio:predict", response_model=PredictionResult)
def predict_audio(request: AudioPredictionInput, service=Depends(get_prediction_service)):
    try:
        return service.predict_audio(request)
    except FeatureNotReadyError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc


@router.post("/vision:predict", response_model=PredictionResult)
def predict_vision(request: VisionPredictionInput, service=Depends(get_prediction_service)):
    try:
        return service.predict_vision(request)
    except FeatureNotReadyError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc


@router.post("/multimodal:predict", response_model=PredictionResult)
def predict_multimodal(request: MultimodalPredictionInput, service=Depends(get_prediction_service)):
    try:
        return service.predict_multimodal(request)
    except FeatureNotReadyError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
