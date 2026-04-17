from typing import Protocol

from depression_detection.model.schemas import (
    AudioPredictionInput,
    MultimodalPredictionInput,
    PredictionResult,
    TextPredictionInput,
    VisionPredictionInput,
)


class TextPredictor(Protocol):
    def predict(self, request: TextPredictionInput) -> PredictionResult: ...


class AudioPredictor(Protocol):
    def predict(self, request: AudioPredictionInput) -> PredictionResult: ...


class VisionPredictor(Protocol):
    def predict(self, request: VisionPredictionInput) -> PredictionResult: ...


class MultimodalPredictor(Protocol):
    def predict(self, request: MultimodalPredictionInput) -> PredictionResult: ...
