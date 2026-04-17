from depression_detection.domain.enums import PredictionLabel
from depression_detection.model.schemas import PredictionResult, VisionPredictionInput


class LocalVisionPredictor:
    def predict(self, request: VisionPredictionInput) -> PredictionResult:
        evidence = [value for value in [request.video_path, *request.image_paths] if value]
        analysis = request.metadata.get("placeholder_analysis") or "当前阶段暂未启用视觉抑郁识别模型，返回默认占位结果。"
        return PredictionResult(
            sample_id=request.sample_id,
            task_type=request.task_type,
            modality=request.modality,
            label=PredictionLabel.UNCERTAIN,
            score=0.0,
            confidence=0.0,
            evidence=evidence,
            analysis=analysis,
            auxiliary_outputs={"placeholder": True},
            model_name="LocalVisionPredictor",
            model_version="placeholder-vision-v1",
        )
