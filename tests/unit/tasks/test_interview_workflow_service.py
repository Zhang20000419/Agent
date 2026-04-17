import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from depression_detection.application.services.archive_service import ArchiveService
from depression_detection.application.services.session_workflow_service import SessionWorkflowService
from depression_detection.config.settings import RuntimeSettings
from depression_detection.domain.enums import Modality, PredictionLabel, TaskType
from depression_detection.model.schemas import PredictionResult
from depression_detection.tasks.qa.schemas import TurnAnalysis


class _DummyQAService:
    def analyze_turn(self, question_id: int, answer: str, *args):
        return TurnAnalysis(
            question_id=question_id,
            question_text="最近2周，你的心情怎么样？",
            answer=answer,
            symptom="情绪低落",
            duration="less_than_2_weeks",
            duration_text="最近两周",
            frequency="sometimes",
            frequency_text="有时",
            severity="mild",
            polarity="support",
            confidence=0.8,
            evidence=[answer],
            explanation="根据转写结果生成。",
            review_notes="复核通过。",
            risk_flag=True,
            review_passed=True,
            retry_count=0,
            review_issues=[],
        )


class _DummyPredictionService:
    def predict_vision(self, request):
        return PredictionResult(
            sample_id=request.sample_id,
            task_type=request.task_type,
            modality=Modality.VISION,
            label=PredictionLabel.UNCERTAIN,
            score=0.0,
            confidence=0.0,
            evidence=[request.video_path] if request.video_path else [],
            analysis=request.metadata.get("placeholder_analysis", ""),
            auxiliary_outputs={"placeholder": True},
            model_name="vision-placeholder",
            model_version="v1",
        )

    def predict_audio(self, request):
        return PredictionResult(
            sample_id=request.sample_id,
            task_type=request.task_type,
            modality=Modality.AUDIO,
            label=PredictionLabel.UNCERTAIN,
            score=0.0,
            confidence=0.0,
            evidence=[request.audio_path],
            analysis=request.metadata.get("placeholder_analysis", ""),
            auxiliary_outputs={"placeholder": True},
            model_name="audio-placeholder",
            model_version="v1",
        )


class _DummyInterviewAnalysisService:
    def __init__(self):
        self.enqueued: list[tuple[str, int]] = []

    def enqueue_qa_analysis(self, session_id: str, question_id: int):
        self.enqueued.append((session_id, question_id))

    def build_stage_placeholder_result(self, sample_id: str, task_type: TaskType, modality: Modality, evidence_path: str, analysis: str):
        return _DummyPredictionService().predict_vision(
            Mock(sample_id=sample_id, task_type=task_type, modality=modality, video_path=evidence_path, metadata={"placeholder_analysis": analysis})
        ) if modality == Modality.VISION else _DummyPredictionService().predict_audio(
            Mock(sample_id=sample_id, task_type=task_type, modality=modality, audio_path=evidence_path, metadata={"placeholder_analysis": analysis})
        )


class InterviewWorkflowServiceTests(unittest.TestCase):
    def test_submit_qa_capture_queues_background_analysis_and_archives_capture(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = RuntimeSettings(interview_archive_root=temp_dir, keep_temp_files=False)
            archive_service = ArchiveService(settings)
            analysis_service = _DummyInterviewAnalysisService()
            workflow = SessionWorkflowService(archive_service, _DummyPredictionService(), analysis_service, settings)
            session = archive_service.create_or_load_session("session-demo")
            result = workflow.submit_qa_capture(
                session.session_id,
                1,
                b"video-bytes",
                "capture.webm",
                "video/webm",
            )

            qa_dir = Path(temp_dir) / session.session_id / "qa" / "q01"
            self.assertTrue((qa_dir / "capture.webm").exists())
            self.assertTrue((qa_dir / "diagnosis.json").exists())
            self.assertEqual(result.record.diagnosis.status, "queued")
            self.assertEqual(analysis_service.enqueued, [("session-demo", 1)])

    def test_submit_movie_capture_returns_completed_placeholder_result(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = RuntimeSettings(interview_archive_root=temp_dir)
            workflow = SessionWorkflowService(ArchiveService(settings), _DummyPredictionService(), _DummyInterviewAnalysisService(), settings)
            session = workflow.create_session().session

            result = workflow.submit_movie_capture(
                session.session_id,
                "positive",
                b"video-bytes",
                "capture.webm",
                "video/webm",
            )

            self.assertEqual(result.record.diagnosis.status, "completed")
            self.assertIn("暂不进行抑郁识别分析", result.record.diagnosis.result["analysis"])
            self.assertTrue((Path(temp_dir) / session.session_id / "movie" / "positive" / "capture.webm").exists())


if __name__ == "__main__":
    unittest.main()
