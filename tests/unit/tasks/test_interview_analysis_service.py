import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from depression_detection.application.services.archive_service import ArchiveService
from depression_detection.application.services.interview_analysis_service import InterviewAnalysisService
from depression_detection.application.services.prediction_service import PredictionServiceFacade
from depression_detection.config.settings import RuntimeSettings
from depression_detection.domain.enums import Modality, PredictionLabel, TaskType
from depression_detection.model.registry import ModelRegistry
from depression_detection.model.schemas import PredictionResult
from depression_detection.preprocessing.schemas import TranscriptionResult
from depression_detection.preprocessing.transcription.service import TranscriptionService
from depression_detection.tasks.interview.schemas import DiagnosisEnvelope, StageArtifactRefs, StageRecord
from depression_detection.tasks.qa.schemas import SessionAnalysis, TurnAnalysis


class _PrimaryTranscriber:
    def transcribe(self, audio_path: str) -> TranscriptionResult:
        return TranscriptionResult(text="转写后的回答", language="zh", provider="whisper")


class _PlaceholderPredictor:
    def __init__(self, modality: Modality):
        self.modality = modality

    def predict(self, request):
        return PredictionResult(
            sample_id=request.sample_id,
            task_type=request.task_type,
            modality=self.modality,
            label=PredictionLabel.UNCERTAIN if self.modality != Modality.MULTIMODAL else PredictionLabel.DEPRESSION,
            score=0.66 if self.modality == Modality.MULTIMODAL else 0.0,
            confidence=0.82 if self.modality == Modality.MULTIMODAL else 0.0,
            evidence=[value for value in [getattr(request, "video_path", None), getattr(request, "audio_path", None), getattr(request, "text", None)] if value],
            analysis="placeholder-analysis",
            auxiliary_outputs=request.metadata,
            model_name=f"{self.modality.value}-predictor",
            model_version="v1",
        )


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

    def summarize_session_from_turns(self, session_id: str, turns):
        return SessionAnalysis(
            session_id=session_id,
            turns=[TurnAnalysis.model_validate(turn) for turn in turns],
            overall_risk="medium",
            session_classification=["depression"],
            overall_confidence=0.88,
            summary="综合文本分析后，存在明显抑郁线索。",
            symptom_summary=["情绪低落"],
            key_findings=["多题回答出现低落和担忧描述"],
            missing_information=[],
            explanation="文本模态综合分析提示抑郁风险。",
        )


class InterviewAnalysisServiceTests(unittest.TestCase):
    def test_run_qa_analysis_persists_transcript_and_session_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = RuntimeSettings(interview_archive_root=temp_dir, interview_analysis_workers=1)
            archive_service = ArchiveService(settings)
            session = archive_service.create_or_load_session("session-demo")
            session.question_count = 1
            session.questions = session.questions[:1]
            capture_path = archive_service.capture_path(session.session_id, "qa", "q01", "capture.webm", "video/webm")
            archive_service.write_bytes(capture_path, b"video")
            diagnosis = DiagnosisEnvelope(status="queued", modality_plan=["vision", "audio", "text"], requested_at=archive_service.now())
            session.stages["qa"]["q01"] = StageRecord(
                item_key="q01",
                item_label="question-1",
                stage="qa",
                artifacts=StageArtifactRefs(capture=archive_service.session_relative_path(session.session_id, capture_path)),
                diagnosis=diagnosis,
            )
            archive_service.save_session(session)

            registry = ModelRegistry()
            registry.register(Modality.AUDIO, _PlaceholderPredictor(Modality.AUDIO))
            registry.register(Modality.VISION, _PlaceholderPredictor(Modality.VISION))
            registry.register(Modality.MULTIMODAL, _PlaceholderPredictor(Modality.MULTIMODAL))
            prediction_service = PredictionServiceFacade(registry)
            transcription_service = TranscriptionService(settings, _PrimaryTranscriber(), None)
            service = InterviewAnalysisService(
                archive_service=archive_service,
                prediction_service=prediction_service,
                qa_service=_DummyQAService(),
                transcription_service=transcription_service,
                settings=settings,
            )

            prepared_audio = Path(temp_dir) / "prepared.wav"
            prepared_audio.write_bytes(b"audio")
            with patch(
                "depression_detection.preprocessing.transcription.service.prepare_audio_for_transcription",
                return_value=prepared_audio,
            ):
                service._run_qa_analysis(session.session_id, 1)

            updated = archive_service.load_session(session.session_id)
            record = updated.stages["qa"]["q01"]
            self.assertEqual(record.diagnosis.status, "completed")
            self.assertEqual(record.artifacts.audio, "qa/q01/audio.wav")
            self.assertEqual(record.artifacts.transcript, "qa/q01/transcript.json")
            self.assertEqual(updated.analysis_summary.status, "completed")
            self.assertEqual(updated.analysis_summary.text.label, PredictionLabel.DEPRESSION)
            self.assertEqual(updated.analysis_summary.multimodal.label, PredictionLabel.DEPRESSION)
            transcript_text = (Path(temp_dir) / session.session_id / "qa" / "q01" / "transcript.json").read_text(encoding="utf-8")
            self.assertIn('"prepared_audio_path": "qa/q01/audio.wav"', transcript_text)


if __name__ == "__main__":
    unittest.main()
