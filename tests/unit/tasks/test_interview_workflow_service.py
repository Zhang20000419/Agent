import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from depression_detection.application.services.archive_service import ArchiveService
from depression_detection.application.services.session_workflow_service import SessionWorkflowService
from depression_detection.config.settings import RuntimeSettings
from depression_detection.preprocessing.schemas import TranscriptionResult
from depression_detection.preprocessing.transcription.service import TranscriptionService
from depression_detection.tasks.qa.schemas import TurnAnalysis


class _PrimaryTranscriber:
    def transcribe(self, audio_path: str) -> TranscriptionResult:
        return TranscriptionResult(text="转写后的回答", language="zh", provider="whisper")


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


class InterviewWorkflowServiceTests(unittest.TestCase):
    def test_submit_qa_capture_persists_archive_audio_transcript_and_diagnosis(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = RuntimeSettings(
                interview_archive_root=temp_dir,
                media_temp_dir=temp_dir,
                keep_temp_files=False,
            )
            archive_service = ArchiveService(settings)
            transcription_service = TranscriptionService(settings, _PrimaryTranscriber(), None)
            workflow = SessionWorkflowService(archive_service, _DummyQAService(), transcription_service, settings)
            session = archive_service.create_or_load_session("session-demo")

            prepared_audio = Path(temp_dir) / "prepared.wav"
            prepared_audio.write_bytes(b"audio")
            with patch(
                "depression_detection.preprocessing.transcription.service.prepare_audio_for_transcription",
                return_value=prepared_audio,
            ):
                result = workflow.submit_qa_capture(
                    session.session_id,
                    1,
                    b"video-bytes",
                    "capture.webm",
                    "video/webm",
                )

            qa_dir = Path(temp_dir) / session.session_id / "qa" / "q01"
            self.assertTrue((qa_dir / "capture.webm").exists())
            self.assertTrue((qa_dir / "audio.wav").exists())
            self.assertTrue((qa_dir / "transcript.json").exists())
            self.assertTrue((qa_dir / "diagnosis.json").exists())
            self.assertEqual(result.record.diagnosis.status, "completed")
            self.assertEqual(result.record.artifacts.audio, "qa/q01/audio.wav")
            self.assertEqual(result.record.artifacts.transcript, "qa/q01/transcript.json")

            transcript_text = (qa_dir / "transcript.json").read_text(encoding="utf-8")
            self.assertIn('"provider": "whisper"', transcript_text)
            self.assertIn('"prepared_audio_path": "qa/q01/audio.wav"', transcript_text)

    def test_submit_movie_capture_can_archive_even_when_model_is_pending(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = RuntimeSettings(interview_archive_root=temp_dir, media_temp_dir=temp_dir)
            workflow = SessionWorkflowService(ArchiveService(settings), _DummyQAService(), None, settings)
            session = workflow.create_session().session

            result = workflow.submit_movie_capture(
                session.session_id,
                "positive",
                b"video-bytes",
                "capture.webm",
                "video/webm",
            )

            self.assertEqual(result.record.diagnosis.status, "pending_model")
            self.assertTrue((Path(temp_dir) / session.session_id / "movie" / "positive" / "capture.webm").exists())


if __name__ == "__main__":
    unittest.main()
