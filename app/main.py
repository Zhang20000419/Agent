from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from depression_detection.bootstrap.container import get_container
from depression_detection.config.settings import get_runtime_settings
from depression_detection.interfaces.api.main import create_app
from depression_detection.interfaces.api.qa_handlers import (
    get_questions_response,
    predict_session_response,
    predict_turn_response,
)
from depression_detection.interfaces.api.request_parsing import parse_turn_request
from depression_detection.tasks.qa.schemas import HealthResponse, SessionAnalysis, SessionInput, TurnAnalysis, TurnInput

settings = get_runtime_settings()
app = create_app(title=settings.app_name, version=settings.version)
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


def _qa_service():
    return get_container().qa_service()


@app.get("/")
def index():
    return FileResponse(static_dir / "index.html")


@app.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(status="ok")


@app.get("/api/questions")
def get_questions():
    return get_questions_response(_qa_service())


def analyze_turn_api(request: TurnInput, answer_audio_bytes: bytes | None = None):
    return predict_turn_response(request, _qa_service(), answer_audio_bytes)


@app.post("/api/analyze-turn", response_model=TurnAnalysis)
async def analyze_turn_http(request: Request):
    try:
        parsed = await parse_turn_request(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return analyze_turn_api(parsed.turn_input, parsed.answer_audio_bytes)


@app.post("/api/analyze-session", response_model=SessionAnalysis)
def analyze_session_api(request: SessionInput):
    return predict_session_response(request, _qa_service())
