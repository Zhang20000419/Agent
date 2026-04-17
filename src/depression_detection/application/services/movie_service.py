from depression_detection.tasks.movie.service import MovieTaskService


class MovieServiceFacade:
    def __init__(self, service: MovieTaskService) -> None:
        self._service = service

    def predict(self, sample_id: str, video_path: str | None = None, image_paths: list[str] | None = None, transcript: str | None = None):
        return self._service.predict(sample_id=sample_id, video_path=video_path, image_paths=image_paths, transcript=transcript)
