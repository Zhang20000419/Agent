from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from depression_detection.interfaces.api.deps import get_interview_service
from depression_detection.interfaces.api.media_parsing import parse_uploaded_media
from depression_detection.shared.logging import get_logger
from depression_detection.tasks.interview.schemas import InterviewSessionCreateResponse, InterviewSessionState, InterviewStageSubmissionResponse

router = APIRouter(prefix="/api/v1/interviews", tags=["interviews"])
logger = get_logger(__name__)


@router.post("", response_model=InterviewSessionCreateResponse)
async def create_interview_session(service=Depends(get_interview_service)):
    logger.info("Creating interview session")
    return await run_in_threadpool(service.create_session)


@router.get("/{session_id}", response_model=InterviewSessionState)
async def get_interview_session(session_id: str, service=Depends(get_interview_service)):
    try:
        logger.info("Loading interview session %s", session_id)
        return await run_in_threadpool(service.get_session, session_id)
    except FileNotFoundError as exc:
        logger.warning("Interview session not found: %s", session_id)
        raise HTTPException(status_code=404, detail="session not found") from exc


@router.post("/{session_id}/movie/{label}", response_model=InterviewStageSubmissionResponse)
async def submit_movie_capture(session_id: str, label: str, request: Request, service=Depends(get_interview_service)):
    try:
        upload = await parse_uploaded_media(request)
        logger.info("Submitting movie capture: session=%s label=%s filename=%s size=%s", session_id, label, upload.filename, len(upload.data))
        return await run_in_threadpool(
            service.submit_movie_capture,
            session_id,
            label,
            upload.data,
            upload.filename,
            upload.content_type,
        )
    except FileNotFoundError as exc:
        logger.warning("Movie submission session not found: session=%s label=%s", session_id, label)
        raise HTTPException(status_code=404, detail="session not found") from exc
    except ValueError as exc:
        logger.exception("Movie submission failed: session=%s label=%s", session_id, label, exc_info=exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{session_id}/reading/{label}", response_model=InterviewStageSubmissionResponse)
async def submit_reading_capture(session_id: str, label: str, request: Request, service=Depends(get_interview_service)):
    try:
        upload = await parse_uploaded_media(request)
        logger.info("Submitting reading capture: session=%s label=%s filename=%s size=%s", session_id, label, upload.filename, len(upload.data))
        return await run_in_threadpool(
            service.submit_reading_capture,
            session_id,
            label,
            upload.data,
            upload.filename,
            upload.content_type,
        )
    except FileNotFoundError as exc:
        logger.warning("Reading submission session not found: session=%s label=%s", session_id, label)
        raise HTTPException(status_code=404, detail="session not found") from exc
    except ValueError as exc:
        logger.exception("Reading submission failed: session=%s label=%s", session_id, label, exc_info=exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{session_id}/qa/{question_id}", response_model=InterviewStageSubmissionResponse)
async def submit_qa_capture(session_id: str, question_id: int, request: Request, service=Depends(get_interview_service)):
    try:
        upload = await parse_uploaded_media(request)
        logger.info("Submitting QA capture: session=%s question_id=%s filename=%s size=%s", session_id, question_id, upload.filename, len(upload.data))
        return await run_in_threadpool(
            service.submit_qa_capture,
            session_id,
            question_id,
            upload.data,
            upload.filename,
            upload.content_type,
        )
    except FileNotFoundError as exc:
        logger.warning("QA submission session not found: session=%s question_id=%s", session_id, question_id)
        raise HTTPException(status_code=404, detail="session not found") from exc
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "question_id" in detail else 400
        logger.exception("QA submission failed: session=%s question_id=%s", session_id, question_id, exc_info=exc)
        raise HTTPException(status_code=status_code, detail=detail) from exc
