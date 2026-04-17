from depression_detection.config.settings import RuntimeSettings


def prepare_reading_features(
    audio_path: str,
    transcript: str | None = None,
    settings: RuntimeSettings | None = None,
) -> dict:
    allow_transcript = settings.reading_uses_text_modality if settings else False
    return {
        "audio_path": audio_path,
        "transcript": transcript if allow_transcript else None,
    }
