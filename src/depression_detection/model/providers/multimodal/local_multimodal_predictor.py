from depression_detection.domain.enums import PredictionLabel
from depression_detection.model.schemas import MultimodalPredictionInput, PredictionResult


class LocalMultimodalPredictor:
    def predict(self, request: MultimodalPredictionInput) -> PredictionResult:
        modality_results = request.metadata.get("modality_results") or {}
        vision = self._coerce_result(modality_results.get("vision"))
        audio = self._coerce_result(modality_results.get("audio"))
        text = self._coerce_result(modality_results.get("text"))
        chosen = self._choose_result(text, audio, vision)

        if chosen is None:
            return PredictionResult(
                sample_id=request.sample_id,
                task_type=request.task_type,
                modality=request.modality,
                label=PredictionLabel.UNCERTAIN,
                score=0.0,
                confidence=0.0,
                evidence=[value for value in [request.text, request.audio_path, request.video_path] if value],
                analysis="当前阶段暂未启用多模态融合模型，返回默认占位结果。",
                auxiliary_outputs={"placeholder": True, "modality_results": modality_results},
                model_name="LocalMultimodalPredictor",
                model_version="placeholder-multimodal-v1",
            )

        analysis_parts = []
        if text is not None:
            analysis_parts.append(f"文本模态结论：{text.label}（置信度 {text.confidence:.2f}）。")
        if vision is not None:
            analysis_parts.append(f"视觉模态结论：{vision.label}。")
        if audio is not None:
            analysis_parts.append(f"音频模态结论：{audio.label}。")
        analysis_parts.append("当前融合逻辑优先采用已有可用模态结果；视觉与音频若仍为占位结果，则主要参考文本模态。")

        evidence = []
        for result in (text, audio, vision):
            if result is not None:
                evidence.extend(result.evidence)

        return PredictionResult(
            sample_id=request.sample_id,
            task_type=request.task_type,
            modality=request.modality,
            label=chosen.label,
            score=chosen.score,
            confidence=chosen.confidence,
            evidence=evidence,
            analysis=" ".join(part for part in analysis_parts if part),
            auxiliary_outputs={"modality_results": modality_results},
            model_name="LocalMultimodalPredictor",
            model_version="placeholder-multimodal-v1",
        )

    @staticmethod
    def _choose_result(*results):
        candidates = [result for result in results if result is not None]
        non_uncertain = [result for result in candidates if result.label != PredictionLabel.UNCERTAIN]
        if non_uncertain:
            return max(non_uncertain, key=lambda item: item.confidence)
        return max(candidates, key=lambda item: item.confidence, default=None)

    @staticmethod
    def _coerce_result(payload):
        if not payload:
            return None
        return PredictionResult.model_validate(payload)
