from fastapi import APIRouter, Depends, HTTPException

from depression_detection.interfaces.api.deps import get_movie_service
from depression_detection.model.schemas import PredictionResult
from depression_detection.tasks.movie.schemas import MovieRequest
from depression_detection.shared.exceptions import FeatureNotReadyError

router = APIRouter(prefix="/api/v1", tags=["movie"])


@router.post("/movie:predict", response_model=PredictionResult)
def predict_movie(request: MovieRequest, service=Depends(get_movie_service)):
    try:
        return service.predict(request.sample_id, request.video_path, request.image_paths, request.transcript)
    except FeatureNotReadyError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
