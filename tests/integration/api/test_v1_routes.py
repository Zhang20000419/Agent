import unittest

from fastapi.testclient import TestClient

from depression_detection.domain.enums import Modality, PredictionLabel, TaskType
from depression_detection.interfaces.api.deps import get_prediction_service, get_qa_service
from depression_detection.interfaces.api.main import create_app
from depression_detection.model.schemas import PredictionResult, VisionPredictionInput
from depression_detection.tasks.qa.schemas import SessionAnalysis, TurnAnalysis


class _FakeQAService:
    def get_questions(self):
        return [{"question_id": 1, "question_text": "你今天过得怎么样？"}]

    def analyze_turn(
        self,
        question_id: int,
        answer: str,
        answer_audio_path: str | None = None,
        answer_audio_base64: str | None = None,
        answer_audio_filename: str | None = None,
        answer_audio_content_type: str | None = None,
        answer_audio_bytes: bytes | None = None,
    ):
        audio_marker = answer_audio_base64 or answer_audio_path
        if answer_audio_bytes is not None:
            decoded = answer_audio_bytes.decode("utf-8", errors="ignore")
            audio_marker = f"upload:{answer_audio_filename}:{answer_audio_content_type}:{decoded}"
        final_answer = answer or f"transcribed:{audio_marker}"
        return TurnAnalysis(
            question_id=question_id,
            question_text="最近2周，你的心情怎么样？",
            answer=final_answer,
            symptom="情绪低落",
            duration="less_than_2_weeks",
            duration_text="最近两周",
            frequency="sometimes",
            frequency_text="有时",
            severity="mild",
            polarity="support",
            confidence=0.8,
            evidence=[final_answer],
            explanation="根据回答提取。",
            review_notes="复核通过。",
            risk_flag=True,
            review_passed=True,
            retry_count=0,
            review_issues=[],
        )

    def analyze_session(self, session_id: str, responses=None, turns=None):
        turn = self.analyze_turn(6, "最近两周有点低落")
        return SessionAnalysis(
            session_id=session_id,
            turns=[turn],
            overall_risk="medium",
            session_classification=["depression"],
            overall_confidence=0.8,
            summary="整场访谈存在抑郁线索。",
            symptom_summary=["近两周情绪低落"],
            key_findings=["回答出现低落描述"],
            missing_information=["功能影响"],
            explanation="基于结构化 turns 得出。",
        )


class _FakePredictionService:
    def predict_vision(self, request: VisionPredictionInput) -> PredictionResult:
        return PredictionResult(
            sample_id=request.sample_id,
            task_type=request.task_type,
            modality=request.modality,
            label=PredictionLabel.HEALTHY,
            score=0.2,
            confidence=0.7,
            evidence=request.image_paths,
            auxiliary_outputs={},
            model_name="fake-vision",
            model_version="v1",
        )

    def predict_text(self, request):
        raise NotImplementedError

    def predict_audio(self, request):
        raise NotImplementedError

    def predict_multimodal(self, request):
        raise NotImplementedError


class V1ApiRouteTests(unittest.TestCase):
    def setUp(self):
        app = create_app()
        app.dependency_overrides[get_qa_service] = lambda: _FakeQAService()
        app.dependency_overrides[get_prediction_service] = lambda: _FakePredictionService()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.app.dependency_overrides.clear()

    def test_v1_qa_routes_work(self):
        questions = self.client.get("/api/v1/qa/questions")
        self.assertEqual(questions.status_code, 200)
        self.assertEqual(questions.json()[0]["question_id"], 1)

        turn = self.client.post("/api/v1/qa/turns:predict", json={"question_id": 6, "answer": "最近两周有点低落"})
        self.assertEqual(turn.status_code, 200)
        self.assertEqual(turn.json()["question_id"], 6)

        session = self.client.post("/api/v1/qa/sessions:predict", json={"session_id": "demo", "responses": [], "turns": [turn.json()]})
        self.assertEqual(session.status_code, 200)
        self.assertEqual(session.json()["session_id"], "demo")

    def test_v1_qa_turn_route_accepts_audio_base64(self):
        turn = self.client.post(
            "/api/v1/qa/turns:predict",
            json={
                "question_id": 6,
                "answer": "",
                "answer_audio_base64": "aGVsbG8=",
                "answer_audio_filename": "demo.wav",
                "answer_audio_content_type": "audio/wav",
            },
        )
        self.assertEqual(turn.status_code, 200)
        self.assertEqual(turn.json()["answer"], "transcribed:aGVsbG8=")

    def test_v1_qa_turn_route_accepts_uploaded_audio_file(self):
        turn = self.client.post(
            "/api/v1/qa/turns:predict",
            data={"question_id": "6", "answer": ""},
            files={"answer_audio": ("demo.wav", b"hello", "audio/wav")},
        )
        self.assertEqual(turn.status_code, 200)
        self.assertEqual(turn.json()["answer"], "transcribed:upload:demo.wav:audio/wav:hello")

    def test_model_layer_vision_route_is_wired(self):
        response = self.client.post(
            "/api/v1/vision:predict",
            json={"sample_id": "s3", "task_type": TaskType.MOVIE.value, "image_paths": ["frame.jpg"], "modality": Modality.VISION.value},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["modality"], Modality.VISION.value)

    def test_unimplemented_task_modalities_return_501(self):
        response = self.client.post("/api/v1/reading:predict", json={"sample_id": "s1", "audio_path": "demo.wav"})
        self.assertEqual(response.status_code, 501)


if __name__ == "__main__":
    unittest.main()
