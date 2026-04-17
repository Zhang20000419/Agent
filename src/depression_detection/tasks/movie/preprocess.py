from depression_detection.config.settings import RuntimeSettings


def prepare_movie_features(
    video_path: str | None = None,
    image_paths: list[str] | None = None,
    transcript: str | None = None,
    settings: RuntimeSettings | None = None,
) -> dict:
    allow_transcript = settings.movie_uses_text_modality if settings else False
    return {
        "video_path": video_path,
        "image_paths": image_paths or [],
        "transcript": transcript if allow_transcript else None,
    }
