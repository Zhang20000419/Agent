from fastapi import HTTPException

from depression_detection.application.validation import validate_session_input, validate_turn_input
from depression_detection.shared.exceptions import TranscriptionError
from depression_detection.tasks.qa.schemas import SessionInput, TurnInput


def get_questions_response(service):
    return service.get_questions()


def predict_turn_response(request: TurnInput, service, answer_audio_bytes: bytes | None = None):
    try:
        validate_turn_input(request, has_uploaded_audio=answer_audio_bytes is not None)
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "question_id" in detail else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    try:
        return service.analyze_turn(
            request.question_id,
            request.answer,
            request.answer_audio_path,
            request.answer_audio_base64,
            request.answer_audio_filename,
            request.answer_audio_content_type,
            answer_audio_bytes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TranscriptionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def predict_session_response(request: SessionInput, service):
    try:
        validate_session_input(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return service.analyze_session(
        session_id=request.session_id,
        responses=[item.model_dump() for item in request.responses],
        turns=request.turns,
    )
