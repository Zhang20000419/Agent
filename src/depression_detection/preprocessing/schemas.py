from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class AudioTranscriptionInput:
    audio_path: str | None = None
    audio_bytes: bytes | None = None
    filename: str | None = None
    content_type: str | None = None


class TranscriptionResult(BaseModel):
    text: str
    language: str
    provider: str
    used_fallback: bool = False
    confidence: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
