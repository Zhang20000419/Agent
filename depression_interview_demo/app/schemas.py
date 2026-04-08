from typing import Literal

from pydantic import BaseModel, Field


Severity = Literal["none", "mild", "moderate", "severe"]
Polarity = Literal["support", "deny", "uncertain"]
OverallRisk = Literal["low", "medium", "high"]
DurationLabel = Literal["none", "less_than_2_weeks", "2_to_4_weeks", "1_to_3_months", "more_than_3_months", "unclear"]
FrequencyLabel = Literal["none", "rare", "sometimes", "often", "almost_every_day", "unclear"]
DepressionClassification = Literal[
    "normal",
    "mild_depression",
    "moderate_depression",
    "moderately_severe_depression",
    "severe_depression",
    "uncertain",
]


class InterviewQuestion(BaseModel):
    question_id: int
    question_text: str


class TurnInput(BaseModel):
    question_id: int
    answer: str


class TurnAnalysis(BaseModel):
    question_id: int
    question_text: str
    answer: str
    symptom: str = Field(description="Main symptom or signal inferred from the answer.")
    duration: DurationLabel
    duration_text: str = Field(description="Original normalized phrase for duration.")
    frequency: FrequencyLabel
    frequency_text: str = Field(description="Original normalized phrase for frequency.")
    severity: Severity
    polarity: Polarity = Field(description="support=回答支持症状存在；deny=回答否定症状存在；uncertain=信息不足或模糊。")
    confidence: float = Field(ge=0.0, le=1.0, description="0到1之间的小数，必须使用阿拉伯数字。")
    evidence: list[str] = Field(description="Evidence strictly grounded in the answer text.")
    explanation: str = Field(description="Short explainable rationale grounded in the evidence.")
    review_notes: str
    risk_flag: bool


class ReviewDecision(BaseModel):
    passed: bool
    issues: list[str]
    guidance_for_retry: str


class SessionInput(BaseModel):
    session_id: str
    responses: list[TurnInput]


class SessionAnalysis(BaseModel):
    session_id: str
    turns: list[TurnAnalysis]
    overall_risk: OverallRisk
    depression_classification: DepressionClassification
    overall_confidence: float = Field(ge=0.0, le=1.0, description="0到1之间的小数，必须使用阿拉伯数字。")
    summary: str
    symptom_summary: list[str]
    key_findings: list[str]
    missing_information: list[str]
    explanation: str


class HealthResponse(BaseModel):
    status: str
