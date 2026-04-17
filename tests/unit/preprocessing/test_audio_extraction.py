import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from depression_detection.config.settings import RuntimeSettings
from depression_detection.preprocessing.audio_extraction import prepare_audio_for_transcription


class AudioExtractionTests(unittest.TestCase):
    def test_prepare_audio_for_transcription_runs_ffmpeg(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "input.wav"
            source.write_bytes(b"demo")

            def fake_run(command, capture_output, text, check):
                Path(command[-1]).write_bytes(b"prepared")
                class Result:
                    returncode = 0
                    stderr = ""
                return Result()

            settings = RuntimeSettings(media_temp_dir=temp_dir)
            with patch("depression_detection.preprocessing.audio_extraction.subprocess.run", side_effect=fake_run):
                prepared = prepare_audio_for_transcription(str(source), settings)

            self.assertTrue(prepared.exists())
            self.assertEqual(prepared.suffix, ".wav")


if __name__ == "__main__":
    unittest.main()
