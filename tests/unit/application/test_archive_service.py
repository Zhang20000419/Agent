import tempfile
import unittest
from pathlib import Path

from depression_detection.application.services.archive_service import ArchiveService
from depression_detection.config.settings import RuntimeSettings


class ArchiveServiceTests(unittest.TestCase):
    def test_archive_service_creates_deterministic_stage_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = ArchiveService(RuntimeSettings(interview_archive_root=temp_dir))
            session = service.create_or_load_session("session-demo")

            movie_capture = service.capture_path(session.session_id, "movie", "positive", "clip.webm", "video/webm")
            reading_audio = service.audio_path(session.session_id, "reading", "neutral")
            qa_transcript = service.transcript_path(session.session_id, "qa", service.qa_item_key(1))

            self.assertEqual(movie_capture, Path(temp_dir).resolve() / "session-demo" / "movie" / "positive" / "capture.webm")
            self.assertEqual(reading_audio, Path(temp_dir).resolve() / "session-demo" / "reading" / "neutral" / "audio.wav")
            self.assertEqual(qa_transcript, Path(temp_dir).resolve() / "session-demo" / "qa" / "q01" / "transcript.json")


if __name__ == "__main__":
    unittest.main()
