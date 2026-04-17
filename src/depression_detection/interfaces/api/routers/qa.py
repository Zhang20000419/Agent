from fastapi import APIRouter, Depends, HTTPException, Request

from depression_detection.interfaces.api.deps import get_qa_service
from depression_detection.interfaces.api.qa_handlers import (
    get_questions_response,
    predict_session_response,
    predict_turn_response,
)
from depression_detection.interfaces.api.request_parsing import parse_turn_request
from depression_detection.tasks.qa.schemas import SessionAnalysis, SessionInput, TurnAnalysis, TurnInput

router = APIRouter(prefix="/api/v1/qa", tags=["qa"])


@router.get("/questions")
def get_questions(service=Depends(get_qa_service)):
    return get_questions_response(service)


@router.post("/turns:predict", response_model=TurnAnalysis)
async def predict_turn(request: Request, service=Depends(get_qa_service)):
    try:
        parsed = await parse_turn_request(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return predict_turn_response(parsed.turn_input, service, parsed.answer_audio_bytes)


@router.post("/sessions:predict", response_model=SessionAnalysis)
def predict_session(request: SessionInput, service=Depends(get_qa_service)):
    return predict_session_response(request, service)
