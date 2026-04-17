import unittest
from unittest.mock import Mock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import analyze_turn_api, app, get_questions, health_check
from depression_detection.shared.exceptions import TranscriptionError
from app.schemas import TurnAnalysis, TurnInput


class ApiCompatRegressionTests(unittest.TestCase):
    def test_health_check_returns_ok(self):
        result = health_check()
        self.assertEqual(result.status, "ok")

    def test_get_questions_returns_fixed_bank(self):
        questions = get_questions()
        self.assertEqual(questions[0].question_id, 1)
        self.assertEqual(questions[-1].question_id, 16)

    def test_analyze_turn_rejects_unknown_question_id(self):
        with self.assertRaises(HTTPException) as ctx:
            analyze_turn_api(TurnInput(question_id=999, answer="test"))

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("question_id not found", str(ctx.exception.detail))

    def test_analyze_turn_rejects_empty_answer(self):
        with self.assertRaises(HTTPException) as ctx:
            analyze_turn_api(TurnInput(question_id=1, answer="   "))

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("cannot all be empty", str(ctx.exception.detail))

    def test_analyze_turn_accepts_audio_base64_when_answer_missing(self):
        fake_service = Mock()
        fake_service.analyze_turn.return_value = {"ok": True}
        with patch("app.main._qa_service", return_value=fake_service):
            result = analyze_turn_api(
                TurnInput(
                    question_id=1,
                    answer="",
                    answer_audio_base64="aGVsbG8=",
                    answer_audio_filename="demo.wav",
                    answer_audio_content_type="audio/wav",
                )
            )

        fake_service.analyze_turn.assert_called_once_with(1, "", None, "aGVsbG8=", "demo.wav", "audio/wav", None)
        self.assertEqual(result, {"ok": True})

    def test_analyze_turn_maps_transcription_error_to_503(self):
        fake_service = Mock()
        fake_service.analyze_turn.side_effect = TranscriptionError("whisper failed")
        with patch("app.main._qa_service", return_value=fake_service):
            with self.assertRaises(HTTPException) as ctx:
                analyze_turn_api(TurnInput(question_id=1, answer="", answer_audio_path="demo.wav"))

        self.assertEqual(ctx.exception.status_code, 503)
        self.assertIn("whisper failed", str(ctx.exception.detail))

    def test_analyze_turn_rejects_conflicting_audio_inputs(self):
        with self.assertRaises(HTTPException) as ctx:
            analyze_turn_api(
                TurnInput(question_id=1, answer="", answer_audio_path="demo.wav", answer_audio_base64="aGVsbG8=")
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("provide only one", str(ctx.exception.detail))

    def test_analyze_turn_maps_local_audio_path_disabled_to_400(self):
        fake_service = Mock()
        fake_service.analyze_turn.side_effect = ValueError("answer_audio_path is disabled; use answer_audio_base64 for external clients")
        with patch("app.main._qa_service", return_value=fake_service):
            with self.assertRaises(HTTPException) as ctx:
                analyze_turn_api(TurnInput(question_id=1, answer="", answer_audio_path="demo.wav"))

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("answer_audio_path is disabled", str(ctx.exception.detail))

    def test_analyze_turn_http_accepts_uploaded_audio_file(self):
        fake_service = Mock()
        fake_service.analyze_turn.return_value = TurnAnalysis(
            question_id=1,
            question_text="你今天过得怎么样？",
            answer="转写后的回答",
            symptom="情绪低落",
            duration="less_than_2_weeks",
            duration_text="最近两周",
            frequency="sometimes",
            frequency_text="有时",
            severity="mild",
            polarity="support",
            confidence=0.8,
            evidence=["转写后的回答"],
            explanation="根据上传音频转写得出。",
            review_notes="复核通过。",
            risk_flag=True,
            review_passed=True,
            retry_count=0,
            review_issues=[],
        )
        client = TestClient(app)
        with patch("app.main._qa_service", return_value=fake_service):
            response = client.post(
                "/api/analyze-turn",
                data={"question_id": "1", "answer": ""},
                files={"answer_audio": ("demo.wav", b"hello", "audio/wav")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], "转写后的回答")
        fake_service.analyze_turn.assert_called_once_with(1, "", None, None, "demo.wav", "audio/wav", b"hello")


if __name__ == "__main__":
    unittest.main()
