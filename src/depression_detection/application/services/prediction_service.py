from depression_detection.domain.enums import Modality, TaskType
from depression_detection.model.registry import ModelRegistry
from depression_detection.model.schemas import (
    AudioPredictionInput,
    MultimodalPredictionInput,
    PredictionResult,
    TextPredictionInput,
    VisionPredictionInput,
)


class PredictionServiceFacade:
    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    def predict_text(self, request: TextPredictionInput) -> PredictionResult:
        return self._registry.get_text_predictor().predict(request)

    def predict_audio(self, request: AudioPredictionInput) -> PredictionResult:
        return self._registry.get_audio_predictor().predict(request)

    def predict_vision(self, request: VisionPredictionInput) -> PredictionResult:
        return self._registry.get_vision_predictor().predict(request)

    def predict_multimodal(self, request: MultimodalPredictionInput) -> PredictionResult:
        return self._registry.get_multimodal_predictor().predict(request)
