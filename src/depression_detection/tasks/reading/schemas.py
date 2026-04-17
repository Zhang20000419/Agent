from pydantic import BaseModel, Field


class ReadingRequest(BaseModel):
    sample_id: str
    audio_path: str
    transcript: str | None = Field(
        default=None,
        description="当前 QA 阶段默认忽略该字段；仅在显式开启 READING_USES_TEXT_MODALITY 时才会使用。",
    )
