from fastapi import FastAPI

from depression_detection.interfaces.api.routers.health import router as health_router
from depression_detection.interfaces.api.routers.interviews import router as interviews_router
from depression_detection.interfaces.api.routers.movie import router as movie_router
from depression_detection.interfaces.api.routers.predictions import router as prediction_router
from depression_detection.interfaces.api.routers.qa import router as qa_router
from depression_detection.interfaces.api.routers.reading import router as reading_router


def create_app(title: str = "Mental Interview Demo", version: str = "0.1.0") -> FastAPI:
    app = FastAPI(title=title, version=version)
    app.include_router(health_router)
    app.include_router(interviews_router)
    app.include_router(qa_router)
    app.include_router(reading_router)
    app.include_router(movie_router)
    app.include_router(prediction_router)
    return app
