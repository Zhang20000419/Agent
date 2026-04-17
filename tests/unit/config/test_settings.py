import os
import unittest
from unittest.mock import patch

from depression_detection.config.settings import RuntimeSettings, _default_ffmpeg_binary


class RuntimeSettingsTests(unittest.TestCase):
    @patch.dict(
        os.environ,
        {
            "APP_HOST": "0.0.0.0",
            "APP_PORT": "9000",
            "CURRENT_STAGE": "qa",
            "QA_AUDIO_TRANSCRIPTION_ENABLED": "true",
            "ALLOW_LOCAL_AUDIO_PATH_INPUT": "false",
            "MOVIE_USES_TEXT_MODALITY": "false",
            "READING_USES_TEXT_MODALITY": "false",
            "TRANSCRIPTION_ENABLED": "true",
            "TRANSCRIPTION_PRIMARY": "whisper",
            "TRANSCRIPTION_FALLBACK": "baidu",
            "ENABLE_BAIDU_FALLBACK": "true",
            "WHISPER_MODEL_NAME": "small",
            "BAIDU_ASR_TIMEOUT_SECONDS": "45",
            "FFMPEG_TIMEOUT_SECONDS": "90",
            "INTERVIEW_QUESTION_DIR": "app/static/interview-assets/interview",
            "INTERVIEW_ARCHIVE_ROOT": "/tmp/interviews",
            "INTERVIEW_ANALYSIS_WORKERS": "2",
            "INTERVIEW_LOG_DIR": "/tmp/interview-logs",
            "TEMP_CLEANUP_MAX_AGE_SECONDS": "600",
        },
        clear=False,
    )
    def test_runtime_settings_parse_current_phase_flags(self):
        settings = RuntimeSettings.from_env()
        self.assertEqual(settings.host, "0.0.0.0")
        self.assertEqual(settings.port, 9000)
        self.assertEqual(settings.current_stage, "qa")
        self.assertTrue(settings.qa_audio_transcription_enabled)
        self.assertFalse(settings.allow_local_audio_path_input)
        self.assertFalse(settings.movie_uses_text_modality)
        self.assertFalse(settings.reading_uses_text_modality)
        self.assertTrue(settings.transcription_enabled)
        self.assertEqual(settings.transcription_primary, "whisper")
        self.assertEqual(settings.transcription_fallback, "baidu")
        self.assertTrue(settings.enable_baidu_fallback)
        self.assertEqual(settings.whisper_model_name, "small")
        self.assertEqual(settings.baidu_asr_timeout_seconds, 45)
        self.assertEqual(settings.ffmpeg_timeout_seconds, 90)
        self.assertEqual(settings.interview_question_dir, "app/static/interview-assets/interview")
        self.assertEqual(settings.interview_archive_root, "/tmp/interviews")
        self.assertEqual(settings.interview_analysis_workers, 2)
        self.assertEqual(settings.interview_log_dir, "/tmp/interview-logs")
        self.assertEqual(settings.temp_cleanup_max_age_seconds, 600)


if __name__ == "__main__":
    unittest.main()


class RuntimeBinaryDetectionTests(unittest.TestCase):
    @patch("depression_detection.config.settings.os.path.exists", side_effect=lambda value: value == "/opt/homebrew/bin/ffmpeg")
    @patch("depression_detection.config.settings.shutil.which", return_value=None)
    def test_default_ffmpeg_binary_prefers_homebrew_path(self, *_):
        self.assertEqual(_default_ffmpeg_binary(), "/opt/homebrew/bin/ffmpeg")
