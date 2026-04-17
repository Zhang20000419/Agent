import json
import re

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from depression_detection.config.model_settings import build_chat_model
from depression_detection.domain.enums import PredictionLabel
from depression_detection.model.schemas import PredictionResult, TextPredictionInput


class _TextPredictionPayload(BaseModel):
    label: PredictionLabel
    score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    explanation: str = ""


class LLMTextPredictor:
    def __init__(self, model_factory=build_chat_model) -> None:
        self._model_factory = model_factory
        self._model = None
        self._parser = PydanticOutputParser(pydantic_object=_TextPredictionPayload)

    def _get_model(self):
        if self._model is None:
            self._model = self._model_factory()
        return self._model

    def invoke(self, prompt: str):
        return self._get_model().invoke(prompt)

    @staticmethod
    def _clean_json_text(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        text = re.sub(r"//.*", "", text)
        return text.strip()

    def predict(self, request: TextPredictionInput) -> PredictionResult:
        prompt = (
            "你是抑郁识别模型层中的 text predictor。"
            "请基于输入文本给出最保守的心理风险标签预测，"
            "标签只能是 healthy/depression/anxiety/bipolar/uncertain。\n\n"
            "要求：严格返回 JSON；evidence 必须来自原文；不要做临床诊断。\n\n"
            f"{self._parser.get_format_instructions()}\n\n"
            f"task_type: {request.task_type.value}\n"
            f"text: {request.text}\n"
            f"metadata: {json.dumps(request.metadata, ensure_ascii=False)}\n"
        )
        response = self.invoke(prompt)
        content = response.content
        if not isinstance(content, str):
            if isinstance(content, list):
                content = "\n".join(
                    item.get("text", str(item)) if isinstance(item, dict) else str(item)
                    for item in content
                )
            else:
                content = str(content)
        try:
            parsed = self._parser.parse(content)
        except Exception:
            payload = json.loads(self._clean_json_text(content))
            parsed = _TextPredictionPayload.model_validate(payload)
        return PredictionResult(
            sample_id=request.sample_id,
            task_type=request.task_type,
            modality=request.modality,
            label=parsed.label,
            score=parsed.score,
            confidence=parsed.confidence,
            evidence=parsed.evidence,
            analysis=parsed.explanation,
            auxiliary_outputs={"explanation": parsed.explanation},
            model_name=type(self._get_model()).__name__,
            model_version="llm-text-v1",
        )
