from depression_detection.bootstrap.container import get_container
from depression_detection.tasks.qa.schemas import SessionAnalysis, TurnAnalysis


def _service():
    return get_container().qa_service()


def analyze_turn(
    question_id: int,
    answer: str,
    answer_audio_path: str | None = None,
    answer_audio_base64: str | None = None,
    answer_audio_filename: str | None = None,
    answer_audio_content_type: str | None = None,
    answer_audio_bytes: bytes | None = None,
) -> TurnAnalysis:
    return _service().analyze_turn(
        question_id,
        answer,
        answer_audio_path,
        answer_audio_base64,
        answer_audio_filename,
        answer_audio_content_type,
        answer_audio_bytes,
    )


def summarize_session_from_turns(session_id: str, turns: list[dict] | list[TurnAnalysis]) -> SessionAnalysis:
    return _service().summarize_session_from_turns(session_id, turns)


def analyze_session(
    session_id: str,
    responses: list[dict] | None = None,
    turns: list[dict] | list[TurnAnalysis] | None = None,
) -> SessionAnalysis:
    return _service().analyze_session(session_id=session_id, responses=responses, turns=turns)
