from depression_detection.config.settings import RuntimeSettings
from depression_detection.domain.enums import Modality, TaskType
from depression_detection.model.registry import ModelRegistry
from depression_detection.model.schemas import MultimodalPredictionInput, PredictionResult
from depression_detection.tasks.movie.preprocess import prepare_movie_features


class MovieTaskService:
    def __init__(self, registry: ModelRegistry, settings: RuntimeSettings) -> None:
        self._registry = registry
        self._settings = settings

    def predict(self, sample_id: str, video_path: str | None = None, image_paths: list[str] | None = None, transcript: str | None = None) -> PredictionResult:
        features = prepare_movie_features(
            video_path=video_path,
            image_paths=image_paths,
            transcript=transcript,
            settings=self._settings,
        )
        predictor = self._registry.get_multimodal_predictor()
        request = MultimodalPredictionInput(
            sample_id=sample_id,
            task_type=TaskType.MOVIE,
            modality=Modality.MULTIMODAL,
            text=features["transcript"],
            video_path=features["video_path"],
            image_paths=features["image_paths"],
        )
        return predictor.predict(request)
