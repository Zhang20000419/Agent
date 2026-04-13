import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from app import pipeline
from app.main import analyze_session_api
from app.schemas import SessionInput, SessionSummary, TurnAnalysis


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

    def make_summary(self) -> SessionSummary:
        return SessionSummary(
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
        provided_turn = self.make_turn()

        with patch("app.pipeline.analyze_turn", side_effect=AssertionError("should not reanalyze turns")), patch(
            "app.pipeline._invoke_structured", return_value=self.make_summary()
        ) as invoke_mock:
            result = pipeline.analyze_session(
                session_id="session-turns",
                responses=[{"question_id": 6, "answer": "这条原始回答不应被再次使用"}],
                turns=[provided_turn.model_dump(mode="json")],
            )

        self.assertEqual(result.turns[0].question_id, provided_turn.question_id)
        self.assertEqual(result.turns[0].answer, provided_turn.answer)
        self.assertEqual(invoke_mock.call_count, 1)
        summarizer_prompt = invoke_mock.call_args[0][0]
        self.assertIn(provided_turn.answer, summarizer_prompt)
        self.assertNotIn("这条原始回答不应被再次使用", summarizer_prompt)

    def test_analyze_session_falls_back_to_responses(self):
        generated_turn = self.make_turn(answer="只有 responses 时需要补跑单题分析")

        with patch("app.pipeline.analyze_turn", return_value=generated_turn) as analyze_turn_mock, patch(
            "app.pipeline._invoke_structured", return_value=self.make_summary()
        ):
            result = pipeline.analyze_session(
                session_id="session-responses",
                responses=[{"question_id": generated_turn.question_id, "answer": generated_turn.answer}],
            )

        analyze_turn_mock.assert_called_once_with(generated_turn.question_id, generated_turn.answer)
        self.assertEqual(result.turns[0].answer, generated_turn.answer)

    def test_api_rejects_empty_turns_and_responses(self):
        with self.assertRaises(HTTPException) as ctx:
            analyze_session_api(SessionInput(session_id="empty", responses=[], turns=[]))

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("cannot both be empty", str(ctx.exception.detail))

    def test_frontend_submits_turn_results_for_session_summary(self):
        html = Path("app/static/index.html").read_text(encoding="utf-8")
        self.assertIn("turns: turnResults", html)


if __name__ == "__main__":
    unittest.main()
