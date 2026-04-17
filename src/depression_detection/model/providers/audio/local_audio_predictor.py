from depression_detection.model.schemas import AudioPredictionInput, PredictionResult
from depression_detection.shared.exceptions import FeatureNotReadyError


class LocalAudioPredictor:
    def predict(self, request: AudioPredictionInput) -> PredictionResult:
        raise FeatureNotReadyError("Audio predictor will be enabled after the local audio model lands.")
