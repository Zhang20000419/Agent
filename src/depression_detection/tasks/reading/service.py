from depression_detection.config.settings import RuntimeSettings
from depression_detection.domain.enums import Modality, TaskType
from depression_detection.model.registry import ModelRegistry
from depression_detection.model.schemas import AudioPredictionInput, PredictionResult
from depression_detection.tasks.reading.preprocess import prepare_reading_features


class ReadingTaskService:
    def __init__(self, registry: ModelRegistry, settings: RuntimeSettings) -> None:
        self._registry = registry
        self._settings = settings

    def predict(self, sample_id: str, audio_path: str, transcript: str | None = None) -> PredictionResult:
        features = prepare_reading_features(audio_path, transcript, settings=self._settings)
        predictor = self._registry.get_audio_predictor()
        request = AudioPredictionInput(
            sample_id=sample_id,
            task_type=TaskType.READING,
            modality=Modality.AUDIO,
            audio_path=features["audio_path"],
            transcript=features["transcript"],
        )
        return predictor.predict(request)
