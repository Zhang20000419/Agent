from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from depression_detection.interfaces.api.deps import get_debug_service
from depression_detection.interfaces.api.media_parsing import parse_uploaded_media
from depression_detection.shared.logging import get_logger

router = APIRouter(prefix="/api/v1/debug", tags=["debug"])
logger = get_logger(__name__)


@router.post("/qa-chain/{question_id}")
async def debug_qa_chain(question_id: int, request: Request, service=Depends(get_debug_service)):
    try:
        upload = await parse_uploaded_media(request)
        logger.info(
            "Running debug QA chain check: question_id=%s filename=%s size=%s",
            question_id,
            upload.filename,
            len(upload.data),
        )
        return await run_in_threadpool(
            service.check_qa_chain,
            question_id,
            upload.data,
            upload.filename,
            upload.content_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
