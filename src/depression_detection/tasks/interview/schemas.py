from typing import Any, Literal

from pydantic import BaseModel, Field

from depression_detection.model.schemas import PredictionResult
from depression_detection.tasks.qa.schemas import InterviewQuestion


InterviewStage = Literal["movie", "reading", "qa"]
DiagnosisStatus = Literal["queued", "processing", "completed", "pending_model", "failed_preprocessing", "failed_model", "not_requested"]

MOVIE_READING_LABELS = ("positive", "neutral", "negative")
DIAGNOSIS_PENDING_MODEL = "pending_model"


class StageArtifactRefs(BaseModel):
    capture: str | None = None
    audio: str | None = None
    transcript: str | None = None
    diagnosis: str | None = None


class DiagnosisEnvelope(BaseModel):
    status: DiagnosisStatus
    modality_plan: list[str] = Field(default_factory=list)
    requested_at: str
    completed_at: str | None = None
    error: str | None = None
    result: dict[str, Any] | None = None


class StageRecord(BaseModel):
    item_key: str
    item_label: str
    stage: InterviewStage
    artifacts: StageArtifactRefs = Field(default_factory=StageArtifactRefs)
    diagnosis: DiagnosisEnvelope


class InterviewAnalysisSummary(BaseModel):
    status: DiagnosisStatus = "not_requested"
    completed_at: str | None = None
    error: str | None = None
    vision: PredictionResult | None = None
    audio: PredictionResult | None = None
    text: PredictionResult | None = None
    multimodal: PredictionResult | None = None
    text_session_analysis: dict[str, Any] | None = None


class InterviewSessionState(BaseModel):
    session_id: str
    created_at: str
    updated_at: str
    question_count: int = 0
    questions: list[InterviewQuestion] = Field(default_factory=list)
    stages: dict[str, dict[str, StageRecord]] = Field(default_factory=dict)
    analysis_summary: InterviewAnalysisSummary = Field(default_factory=InterviewAnalysisSummary)


class MovieAsset(BaseModel):
    key: str
    title: str
    description: str
    filename: str | None = None
    url: str | None = None


class ReadingAsset(BaseModel):
    key: str
    title: str
    description: str
    filename: str | None = None
    text: str = ""


class InterviewAssetManifest(BaseModel):
    movie: list[MovieAsset] = Field(default_factory=list)
    reading: list[ReadingAsset] = Field(default_factory=list)
    qa_questions: list[InterviewQuestion] = Field(default_factory=list)


class InterviewSessionCreateResponse(BaseModel):
    session: InterviewSessionState
    movie_labels: list[str] = Field(default_factory=lambda: list(MOVIE_READING_LABELS))
    reading_labels: list[str] = Field(default_factory=lambda: list(MOVIE_READING_LABELS))
    assets: InterviewAssetManifest = Field(default_factory=InterviewAssetManifest)


class InterviewStageSubmissionResponse(BaseModel):
    session: InterviewSessionState
    record: StageRecord
