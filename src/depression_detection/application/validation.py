from depression_detection.tasks.qa.question_bank import get_question_index
from depression_detection.tasks.qa.schemas import SessionInput, TurnInput


def _has_value(value: str | None) -> bool:
    return bool((value or "").strip())


def validate_turn_input(request: TurnInput, has_uploaded_audio: bool = False) -> None:
    if request.question_id not in get_question_index():
        raise ValueError("question_id not found")
    audio_source_count = sum(
        [
            _has_value(request.answer_audio_base64),
            _has_value(request.answer_audio_path),
            has_uploaded_audio,
        ]
    )
    if audio_source_count > 1:
        raise ValueError("provide only one of answer_audio_base64, answer_audio_path or uploaded audio")
    if not _has_value(request.answer) and audio_source_count == 0:
        raise ValueError("answer, answer_audio_base64, answer_audio_path and uploaded audio cannot all be empty")


def validate_session_input(request: SessionInput) -> None:
    if not request.turns and not request.responses:
        raise ValueError("turns or responses cannot both be empty")
    for response in request.responses:
        validate_turn_input(response)
