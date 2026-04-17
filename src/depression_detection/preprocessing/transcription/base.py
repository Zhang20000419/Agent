from typing import Protocol

from depression_detection.preprocessing.schemas import TranscriptionResult


class Transcriber(Protocol):
    provider_name: str

    def transcribe(self, audio_path: str) -> TranscriptionResult: ...
