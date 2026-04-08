from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.interview_questions import INTERVIEW_QUESTIONS, QUESTION_INDEX
from app.pipeline import analyze_session, analyze_turn
from app.schemas import HealthResponse, SessionAnalysis, SessionInput, TurnAnalysis, TurnInput

app = FastAPI(title="Depression Interview Demo", version="0.1.0")
static_dir = Path(__file__).parent / "static"

# 前端页面和后端 API 复用同一个 FastAPI 服务，便于本地直接演示。
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def index():
    return FileResponse(static_dir / "index.html")


@app.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(status="ok")


@app.get("/api/questions")
def get_questions():
    return INTERVIEW_QUESTIONS


@app.post("/api/analyze-turn", response_model=TurnAnalysis)
def analyze_turn_api(request: TurnInput):
    # 单题接口用于前端逐题展示中间分析结果。
    if request.question_id not in QUESTION_INDEX:
        raise HTTPException(status_code=404, detail="question_id not found")
    if not request.answer.strip():
        raise HTTPException(status_code=400, detail="answer cannot be empty")
    return analyze_turn(request.question_id, request.answer)


@app.post("/api/analyze-session", response_model=SessionAnalysis)
def analyze_session_api(request: SessionInput):
    # 整场接口用于在多轮分析完成后触发最终综合判断。
    if not request.responses:
        raise HTTPException(status_code=400, detail="responses cannot be empty")
    return analyze_session(
        session_id=request.session_id,
        responses=[item.model_dump() for item in request.responses],
    )
