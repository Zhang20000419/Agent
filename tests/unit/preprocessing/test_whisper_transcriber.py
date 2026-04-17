import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from depression_detection.config.settings import RuntimeSettings
from depression_detection.preprocessing.transcription.whisper_transcriber import WhisperTranscriber


class WhisperTranscriberTests(unittest.TestCase):
    def test_whisper_transcriber_reads_generated_txt(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "input.wav"
            source.write_bytes(b"demo")

            def fake_run(command, capture_output, text, check):
                output_dir = Path(command[command.index("--output_dir") + 1])
                output_dir.mkdir(parents=True, exist_ok=True)
                (output_dir / "input.txt").write_text("转写文本", encoding="utf-8")
                class Result:
                    returncode = 0
                    stderr = ""
                    stdout = ""
                return Result()

            settings = RuntimeSettings()
            transcriber = WhisperTranscriber(settings)
            with patch("depression_detection.preprocessing.transcription.whisper_transcriber.shutil.which", return_value="/usr/bin/whisper"), patch(
                "depression_detection.preprocessing.transcription.whisper_transcriber.subprocess.run",
                side_effect=fake_run,
            ):
                result = transcriber.transcribe(str(source))

            self.assertEqual(result.text, "转写文本")
            self.assertEqual(result.provider, "whisper")


if __name__ == "__main__":
    unittest.main()
