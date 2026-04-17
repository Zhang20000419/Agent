from typing import Literal

from pydantic import BaseModel, Field


# 这些 Literal 约束既是后端校验，也是提示词里要求模型遵守的目标枚举。
Severity = Literal["none", "mild", "moderate", "severe"]
Polarity = Literal["support", "deny", "uncertain"]
OverallRisk = Literal["low", "medium", "high"]
DurationLabel = Literal["none", "less_than_2_weeks", "2_to_4_weeks", "1_to_3_months", "more_than_3_months", "unclear"]
FrequencyLabel = Literal["none", "rare", "sometimes", "often", "almost_every_day", "unclear"]
SessionClassification = Literal[
    "depression",
    "bipolar",
    "anxiety",
    "healthy",
]


class InterviewQuestion(BaseModel):
    question_id: int
    question_text: str


class TurnInput(BaseModel):
    question_id: int
    answer: str = ""
    answer_audio_base64: str | None = Field(
        default=None,
        description="JSON 兼容媒体输入方式；客户端可传 base64 编码的录音或录屏内容。若支持 multipart/form-data，优先使用真实文件上传。",
    )
    answer_audio_filename: str | None = Field(
        default=None,
        description="可选的媒体原始文件名，用于保留扩展名并帮助 ffmpeg 识别格式。",
    )
    answer_audio_content_type: str | None = Field(
        default=None,
        description="可选的 MIME type，例如 audio/wav、audio/webm。",
    )
    answer_audio_path: str | None = Field(
        default=None,
        description="仅供本地 demo / internal 兼容使用的服务端本地媒体路径；远程客户端应优先使用 multipart 上传，其次再使用 answer_audio_base64。",
    )


class TurnAnalysis(BaseModel):
    # 单题输出需要同时兼顾“可机器消费”和“可解释展示”。
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
    review_passed: bool = Field(default=True, description="当前结果是否通过最终复核裁决。")
    retry_count: int = Field(default=0, ge=0, description="本题在通过最终复核前发生的重试次数。")
    review_issues: list[str] = Field(default_factory=list, description="复核过程中发现的问题列表。")


class ReviewDecision(BaseModel):
    passed: bool
    issues: list[str]
    guidance_for_retry: str


class SessionInput(BaseModel):
    session_id: str
    responses: list[TurnInput] = Field(default_factory=list)
    turns: list[TurnAnalysis] = Field(default_factory=list)


class SessionAnalysis(BaseModel):
    # `turns` 保留整场逐题结果，便于前端在最终总结页展示时间线。
    session_id: str
    turns: list[TurnAnalysis]
    overall_risk: OverallRisk
    session_classification: list[SessionClassification] = Field(min_length=1)
    overall_confidence: float = Field(ge=0.0, le=1.0, description="0到1之间的小数，必须使用阿拉伯数字。")
    summary: str
    symptom_summary: list[str]
    key_findings: list[str]
    missing_information: list[str]
    explanation: str


class SessionSummary(BaseModel):
    overall_risk: OverallRisk
    session_classification: list[SessionClassification] = Field(min_length=1)
    overall_confidence: float = Field(ge=0.0, le=1.0, description="0到1之间的小数，必须使用阿拉伯数字。")
    summary: str
    symptom_summary: list[str]
    key_findings: list[str]
    missing_information: list[str]
    explanation: str


class HealthResponse(BaseModel):
    status: str
