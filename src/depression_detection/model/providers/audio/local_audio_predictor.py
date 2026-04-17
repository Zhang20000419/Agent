from depression_detection.domain.enums import PredictionLabel
from depression_detection.model.schemas import AudioPredictionInput, PredictionResult


class LocalAudioPredictor:
    def predict(self, request: AudioPredictionInput) -> PredictionResult:
        analysis = request.metadata.get("placeholder_analysis") or "当前阶段暂未启用音频抑郁识别模型，返回默认占位结果。"
        evidence = [request.audio_path] if request.audio_path else []
        return PredictionResult(
            sample_id=request.sample_id,
            task_type=request.task_type,
            modality=request.modality,
            label=PredictionLabel.UNCERTAIN,
            score=0.0,
            confidence=0.0,
            evidence=evidence,
            analysis=analysis,
            auxiliary_outputs={
                "placeholder": True,
                "transcript": request.transcript,
            },
            model_name="LocalAudioPredictor",
            model_version="placeholder-audio-v1",
        )
