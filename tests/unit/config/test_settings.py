import os
import unittest
from unittest.mock import patch

from depression_detection.config.settings import RuntimeSettings


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
            "INTERVIEW_QUESTION_DIR": "app/static/interview-assets/interview",
            "INTERVIEW_ARCHIVE_ROOT": "/tmp/interviews",
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
        self.assertEqual(settings.interview_question_dir, "app/static/interview-assets/interview")
        self.assertEqual(settings.interview_archive_root, "/tmp/interviews")


if __name__ == "__main__":
    unittest.main()
