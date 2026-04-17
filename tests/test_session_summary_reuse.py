import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from app.main import analyze_session_api
from app.schemas import SessionAnalysis, SessionInput, TurnAnalysis
from depression_detection.tasks.qa.service import QAAnalysisService


class _DummyTextRuntime:
    def invoke(self, prompt: str):
        raise AssertionError(f"unexpected model call: {prompt}")


class _DummyTranscriptionService:
    def transcribe_audio(self, audio_path: str):
        raise AssertionError(f"unexpected transcription call: {audio_path}")


class SessionSummaryReuseTests(unittest.TestCase):
    def make_turn(self, question_id: int = 6, answer: str = "最近两周情绪低落，也常常担心工作出错。") -> TurnAnalysis:
        return TurnAnalysis(
            question_id=question_id,
            question_text="最近2周，你的心情怎么样？",
            answer=answer,
            symptom="情绪低落",
            duration="less_than_2_weeks",
            duration_text="最近两周",
            frequency="often",
            frequency_text="经常",
            severity="moderate",
            polarity="support",
            confidence=0.82,
            evidence=["最近两周情绪低落", "经常担心工作出错"],
            explanation="回答直接提到近两周情绪低落，并伴随明显担忧。",
            review_notes="复核通过。",
            risk_flag=True,
            review_passed=True,
            retry_count=0,
            review_issues=[],
        )

    def make_summary(self, session_id: str, turns: list[TurnAnalysis]) -> SessionAnalysis:
        return SessionAnalysis(
            session_id=session_id,
            turns=turns,
            overall_risk="medium",
            session_classification=["depression", "anxiety"],
            overall_confidence=0.76,
            summary="整场访谈呈现低落与担忧并存。",
            symptom_summary=["持续低落", "焦虑担忧"],
            key_findings=["近两周情绪低落", "经常担心工作出错"],
            missing_information=["睡眠变化", "功能受损程度"],
            explanation="综合已有单题分析，情绪低落与担忧线索并存。",
        )

    def test_analyze_session_prefers_provided_turns(self):
        service = QAAnalysisService(text_runtime=_DummyTextRuntime(), transcription_service=_DummyTranscriptionService())
        provided_turn = self.make_turn()

        with patch.object(service, "_build_turns_from_responses", side_effect=AssertionError("should not reanalyze turns")), patch.object(
            service,
            "summarize_session_from_turns",
            return_value=self.make_summary("session-turns", [provided_turn]),
        ) as summarize_mock:
            result = service.analyze_session(
                session_id="session-turns",
                responses=[{"question_id": 6, "answer": "这条原始回答不应被再次使用"}],
                turns=[provided_turn.model_dump(mode="json")],
            )

        self.assertEqual(result.turns[0].question_id, provided_turn.question_id)
        self.assertEqual(result.turns[0].answer, provided_turn.answer)
        summarize_mock.assert_called_once()
        called_turns = summarize_mock.call_args.kwargs.get("turns") or summarize_mock.call_args.args[1]
        self.assertEqual(called_turns[0]["answer"], provided_turn.answer)

    def test_analyze_session_falls_back_to_responses(self):
        service = QAAnalysisService(text_runtime=_DummyTextRuntime(), transcription_service=_DummyTranscriptionService())
        generated_turn = self.make_turn(answer="只有 responses 时需要补跑单题分析")

        with patch.object(service, "analyze_turn", return_value=generated_turn) as analyze_turn_mock, patch.object(
            service,
            "summarize_session_from_turns",
            return_value=self.make_summary("session-responses", [generated_turn]),
        ) as summarize_mock:
            result = service.analyze_session(
                    session_id="session-responses",
                    responses=[{"question_id": generated_turn.question_id, "answer": generated_turn.answer}],
                )

        analyze_turn_mock.assert_called_once_with(generated_turn.question_id, generated_turn.answer, None, None, None, None, None)
        summarize_mock.assert_called_once()
        self.assertEqual(result.turns[0].answer, generated_turn.answer)

    def test_api_rejects_empty_turns_and_responses(self):
        with self.assertRaises(HTTPException) as ctx:
            analyze_session_api(SessionInput(session_id="empty", responses=[], turns=[]))

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("cannot both be empty", str(ctx.exception.detail))

    def test_frontend_uses_interview_workflow_routes(self):
        html = Path("app/static/index.html").read_text(encoding="utf-8")
        self.assertIn("/api/v1/interviews", html)
        self.assertIn("看电影 → 朗读文字 → 访谈问答", html)
        self.assertIn("/static/interview-assets/interview/", html)
        self.assertIn("payload.assets", html)
        self.assertIn("assetManifest.reading", html)
        self.assertIn("接下来你将看到三段电影片段", html)
        self.assertIn("请休息 10 秒", html)
        self.assertIn("朗读结束", html)
        self.assertIn("下一个问题", html)
        self.assertIn("调试：下一个电影", html)
        self.assertNotIn("调试：下一段朗读", html)
        self.assertIn("analysis_summary", html)
        self.assertIn("正在生成分析结果", html)
        self.assertIn("视觉模态（当前为占位模型）", html)
        self.assertIn("音频模态（当前为占位模型）", html)
        self.assertIn(".cache/logs/interview-backend.log", html)

    def test_frontend_requests_camera_and_microphone_capture(self):
        html = Path("app/static/index.html").read_text(encoding="utf-8")
        self.assertIn("navigator.mediaDevices.getUserMedia", html)
        self.assertIn("MediaRecorder", html)
        self.assertIn("重新连接摄像头 / 麦克风", html)


if __name__ == "__main__":
    unittest.main()
