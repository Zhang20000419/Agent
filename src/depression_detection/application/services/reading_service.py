from depression_detection.tasks.reading.service import ReadingTaskService


class ReadingServiceFacade:
    def __init__(self, service: ReadingTaskService) -> None:
        self._service = service

    def predict(self, sample_id: str, audio_path: str, transcript: str | None = None):
        return self._service.predict(sample_id=sample_id, audio_path=audio_path, transcript=transcript)
