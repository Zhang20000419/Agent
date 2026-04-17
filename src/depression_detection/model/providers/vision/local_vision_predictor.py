from depression_detection.model.schemas import PredictionResult, VisionPredictionInput
from depression_detection.shared.exceptions import FeatureNotReadyError


class LocalVisionPredictor:
    def predict(self, request: VisionPredictionInput) -> PredictionResult:
        raise FeatureNotReadyError("Vision predictor will be enabled after the local vision model lands.")
