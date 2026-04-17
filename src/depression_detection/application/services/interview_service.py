from depression_detection.application.services.session_workflow_service import SessionWorkflowService


class InterviewServiceFacade:
    def __init__(self, service: SessionWorkflowService) -> None:
        self._service = service

    def create_session(self):
        return self._service.create_session()

    def get_session(self, session_id: str):
        return self._service.get_session(session_id)

    def submit_movie_capture(self, session_id: str, label: str, capture_bytes: bytes, filename: str | None, content_type: str | None):
        return self._service.submit_movie_capture(session_id, label, capture_bytes, filename, content_type)

    def submit_reading_capture(self, session_id: str, label: str, capture_bytes: bytes, filename: str | None, content_type: str | None):
        return self._service.submit_reading_capture(session_id, label, capture_bytes, filename, content_type)

    def submit_qa_capture(self, session_id: str, question_id: int, capture_bytes: bytes, filename: str | None, content_type: str | None):
        return self._service.submit_qa_capture(session_id, question_id, capture_bytes, filename, content_type)
