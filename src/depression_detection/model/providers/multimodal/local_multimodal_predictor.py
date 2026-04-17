from depression_detection.model.schemas import MultimodalPredictionInput, PredictionResult
from depression_detection.shared.exceptions import FeatureNotReadyError


class LocalMultimodalPredictor:
    def predict(self, request: MultimodalPredictionInput) -> PredictionResult:
        raise FeatureNotReadyError("Multimodal predictor will be enabled after the local multimodal model lands.")
