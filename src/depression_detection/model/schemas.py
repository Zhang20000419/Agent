from typing import Any

from pydantic import BaseModel, Field, model_validator

from depression_detection.domain.enums import Modality, PredictionLabel, TaskType


class BasePredictionInput(BaseModel):
    sample_id: str
    task_type: TaskType
    modality: Modality
    metadata: dict[str, Any] = Field(default_factory=dict)


class TextPredictionInput(BasePredictionInput):
    modality: Modality = Field(default=Modality.TEXT)
    text: str

    @model_validator(mode="after")
    def validate_modality(self):
        if self.modality != Modality.TEXT:
            raise ValueError("TextPredictionInput modality must be text")
        return self


class AudioPredictionInput(BasePredictionInput):
    modality: Modality = Field(default=Modality.AUDIO)
    audio_path: str
    transcript: str | None = None

    @model_validator(mode="after")
    def validate_modality(self):
        if self.modality != Modality.AUDIO:
            raise ValueError("AudioPredictionInput modality must be audio")
        return self


class VisionPredictionInput(BasePredictionInput):
    modality: Modality = Field(default=Modality.VISION)
    video_path: str | None = None
    image_paths: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_payload(self):
        if self.modality != Modality.VISION:
            raise ValueError("VisionPredictionInput modality must be vision")
        if not self.video_path and not self.image_paths:
            raise ValueError("VisionPredictionInput requires video_path or image_paths")
        return self


class MultimodalPredictionInput(BasePredictionInput):
    modality: Modality = Field(default=Modality.MULTIMODAL)
    text: str | None = None
    audio_path: str | None = None
    video_path: str | None = None
    image_paths: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_payload(self):
        if self.modality != Modality.MULTIMODAL:
            raise ValueError("MultimodalPredictionInput modality must be multimodal")
        if not any([self.text, self.audio_path, self.video_path, self.image_paths]):
            raise ValueError("MultimodalPredictionInput requires at least one modality payload")
        return self


class PredictionResult(BaseModel):
    sample_id: str
    task_type: TaskType
    modality: Modality
    label: PredictionLabel
    score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    analysis: str = ""
    auxiliary_outputs: dict[str, Any] = Field(default_factory=dict)
    model_name: str
    model_version: str
