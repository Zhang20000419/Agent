from pydantic import BaseModel, Field


class MovieRequest(BaseModel):
    sample_id: str
    video_path: str | None = None
    image_paths: list[str] = Field(default_factory=list)
    transcript: str | None = Field(
        default=None,
        description="当前 QA 阶段默认忽略该字段；仅在显式开启 MOVIE_USES_TEXT_MODALITY 时才会使用。",
    )
