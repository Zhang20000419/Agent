from depression_detection.tasks.qa.question_bank import load_interview_questions
from depression_detection.tasks.qa.service import QAAnalysisService
from depression_detection.tasks.qa.schemas import SessionAnalysis, TurnAnalysis


class QAServiceFacade:
    def __init__(self, service: QAAnalysisService) -> None:
        self._service = service

    def get_questions(self):
        return load_interview_questions()

    def analyze_turn(
        self,
        question_id: int,
        answer: str,
        answer_audio_path: str | None = None,
        answer_audio_base64: str | None = None,
        answer_audio_filename: str | None = None,
        answer_audio_content_type: str | None = None,
        answer_audio_bytes: bytes | None = None,
    ) -> TurnAnalysis:
        return self._service.analyze_turn(
            question_id,
            answer,
            answer_audio_path,
            answer_audio_base64,
            answer_audio_filename,
            answer_audio_content_type,
            answer_audio_bytes,
        )

    def analyze_session(self, session_id: str, responses: list[dict] | None = None, turns=None) -> SessionAnalysis:
        return self._service.analyze_session(session_id=session_id, responses=responses, turns=turns)

    def summarize_session_from_turns(self, session_id: str, turns):
        return self._service.summarize_session_from_turns(session_id, turns)
