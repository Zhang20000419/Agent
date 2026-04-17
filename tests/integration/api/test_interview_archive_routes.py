import unittest

from fastapi.testclient import TestClient

from depression_detection.interfaces.api.deps import get_interview_service
from depression_detection.interfaces.api.main import create_app
from depression_detection.tasks.interview.schemas import (
    DiagnosisEnvelope,
    InterviewAssetManifest,
    MovieAsset,
    ReadingAsset,
    InterviewSessionCreateResponse,
    InterviewSessionState,
    InterviewStageSubmissionResponse,
    StageArtifactRefs,
    StageRecord,
)
from depression_detection.tasks.qa.schemas import InterviewQuestion


class _FakeInterviewService:
    def __init__(self):
        self.session = InterviewSessionState(
            session_id="session-demo",
            created_at="2026-04-17T00:00:00+00:00",
            updated_at="2026-04-17T00:00:00+00:00",
            question_count=2,
            questions=[
                InterviewQuestion(question_id=1, question_text="问题一"),
                InterviewQuestion(question_id=2, question_text="问题二"),
            ],
            stages={"movie": {}, "reading": {}, "qa": {}},
        )

    def create_session(self):
        return InterviewSessionCreateResponse(
            session=self.session,
            assets=InterviewAssetManifest(
                movie=[MovieAsset(key="positive", title="正性电影", description="desc", filename="positive.mp4", url="/static/interview-assets/movie/positive/positive.mp4")],
                reading=[ReadingAsset(key="positive", title="正性朗读", description="desc", filename="positive.txt", text="正性文本")],
                qa_questions=self.session.questions,
            ),
        )

    def get_session(self, session_id: str):
        if session_id != self.session.session_id:
            raise FileNotFoundError
        return self.session

    def _record(self, stage: str, item_key: str) -> InterviewStageSubmissionResponse:
        record = StageRecord(
            item_key=item_key,
            item_label=item_key,
            stage=stage,
            artifacts=StageArtifactRefs(capture=f"{stage}/{item_key}/capture.webm", diagnosis=f"{stage}/{item_key}/diagnosis.json"),
            diagnosis=DiagnosisEnvelope(
                status="pending_model" if stage != "qa" else "completed",
                modality_plan=["vision"] if stage == "movie" else ["vision", "audio", "text"],
                requested_at="2026-04-17T00:00:00+00:00",
                completed_at="2026-04-17T00:00:01+00:00" if stage == "qa" else None,
                result={"ok": True} if stage == "qa" else None,
            ),
        )
        self.session.stages.setdefault(stage, {})[item_key] = record
        return InterviewStageSubmissionResponse(session=self.session, record=record)

    def submit_movie_capture(self, session_id: str, label: str, capture_bytes: bytes, filename: str | None, content_type: str | None):
        return self._record("movie", label)

    def submit_reading_capture(self, session_id: str, label: str, capture_bytes: bytes, filename: str | None, content_type: str | None):
        return self._record("reading", label)

    def submit_qa_capture(self, session_id: str, question_id: int, capture_bytes: bytes, filename: str | None, content_type: str | None):
        return self._record("qa", f"q{question_id:02d}")


class InterviewArchiveRouteTests(unittest.TestCase):
    def setUp(self):
        app = create_app()
        self.service = _FakeInterviewService()
        app.dependency_overrides[get_interview_service] = lambda: self.service
        self.client = TestClient(app)

    def tearDown(self):
        self.client.app.dependency_overrides.clear()

    def test_create_session_and_submit_stage_routes(self):
        created = self.client.post("/api/v1/interviews")
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.json()["session"]["session_id"], "session-demo")

        movie = self.client.post(
            "/api/v1/interviews/session-demo/movie/positive",
            files={"capture": ("movie.webm", b"video", "video/webm")},
        )
        self.assertEqual(movie.status_code, 200)
        self.assertEqual(movie.json()["record"]["diagnosis"]["status"], "pending_model")

        reading = self.client.post(
            "/api/v1/interviews/session-demo/reading/neutral",
            files={"capture": ("reading.webm", b"video", "video/webm")},
        )
        self.assertEqual(reading.status_code, 200)

        qa = self.client.post(
            "/api/v1/interviews/session-demo/qa/1",
            files={"capture": ("qa.webm", b"video", "video/webm")},
        )
        self.assertEqual(qa.status_code, 200)
        self.assertEqual(qa.json()["record"]["diagnosis"]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
