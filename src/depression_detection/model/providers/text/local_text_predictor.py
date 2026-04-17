from depression_detection.model.schemas import PredictionResult, TextPredictionInput
from depression_detection.shared.exceptions import FeatureNotReadyError


class LocalTextPredictor:
    def predict(self, request: TextPredictionInput) -> PredictionResult:
        raise FeatureNotReadyError("Local text predictor is not wired to a trained model yet.")
