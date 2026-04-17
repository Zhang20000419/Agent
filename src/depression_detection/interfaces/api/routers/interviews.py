from fastapi import APIRouter, Depends, HTTPException, Request

from depression_detection.interfaces.api.deps import get_interview_service
from depression_detection.interfaces.api.media_parsing import parse_uploaded_media
from depression_detection.tasks.interview.schemas import InterviewSessionCreateResponse, InterviewSessionState, InterviewStageSubmissionResponse

router = APIRouter(prefix="/api/v1/interviews", tags=["interviews"])


@router.post("", response_model=InterviewSessionCreateResponse)
def create_interview_session(service=Depends(get_interview_service)):
    return service.create_session()


@router.get("/{session_id}", response_model=InterviewSessionState)
def get_interview_session(session_id: str, service=Depends(get_interview_service)):
    try:
        return service.get_session(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc


@router.post("/{session_id}/movie/{label}", response_model=InterviewStageSubmissionResponse)
async def submit_movie_capture(session_id: str, label: str, request: Request, service=Depends(get_interview_service)):
    try:
        upload = await parse_uploaded_media(request)
        return service.submit_movie_capture(session_id, label, upload.data, upload.filename, upload.content_type)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{session_id}/reading/{label}", response_model=InterviewStageSubmissionResponse)
async def submit_reading_capture(session_id: str, label: str, request: Request, service=Depends(get_interview_service)):
    try:
        upload = await parse_uploaded_media(request)
        return service.submit_reading_capture(session_id, label, upload.data, upload.filename, upload.content_type)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{session_id}/qa/{question_id}", response_model=InterviewStageSubmissionResponse)
async def submit_qa_capture(session_id: str, question_id: int, request: Request, service=Depends(get_interview_service)):
    try:
        upload = await parse_uploaded_media(request)
        return service.submit_qa_capture(session_id, question_id, upload.data, upload.filename, upload.content_type)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "question_id" in detail else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
