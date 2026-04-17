import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from depression_detection.config.settings import RuntimeSettings
from depression_detection.preprocessing.schemas import AudioTranscriptionInput, TranscriptionResult
from depression_detection.preprocessing.transcription.service import TranscriptionService
from depression_detection.shared.exceptions import TranscriptionError


class _PrimaryTranscriber:
    provider_name = "whisper"

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.calls: list[str] = []

    def transcribe(self, audio_path: str) -> TranscriptionResult:
        self.calls.append(audio_path)
        if self.should_fail:
            raise TranscriptionError("whisper failed")
        return TranscriptionResult(text="主路径文本", language="zh", provider=self.provider_name)


class _FallbackTranscriber:
    provider_name = "baidu"

    def __init__(self):
        self.calls: list[str] = []

    def transcribe(self, audio_path: str) -> TranscriptionResult:
        self.calls.append(audio_path)
        return TranscriptionResult(text="兜底文本", language="zh", provider=self.provider_name)


class TranscriptionServiceTests(unittest.TestCase):
    def test_primary_transcriber_success(self):
        settings = RuntimeSettings(transcription_enabled=True, keep_temp_files=True)
        primary = _PrimaryTranscriber()
        service = TranscriptionService(settings, primary, None)
        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp, patch(
            "depression_detection.preprocessing.transcription.service.prepare_audio_for_transcription",
            return_value=Path(tmp.name),
        ):
            result = service.transcribe_audio(tmp.name)
        self.assertEqual(result.text, "主路径文本")
        self.assertFalse(result.used_fallback)
        self.assertEqual(primary.calls, [tmp.name])

    def test_fallback_transcriber_used_when_primary_fails(self):
        settings = RuntimeSettings(transcription_enabled=True, enable_baidu_fallback=True, keep_temp_files=True)
        primary = _PrimaryTranscriber(should_fail=True)
        fallback = _FallbackTranscriber()
        service = TranscriptionService(settings, primary, fallback)
        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp, patch(
            "depression_detection.preprocessing.transcription.service.prepare_audio_for_transcription",
            return_value=Path(tmp.name),
        ):
            result = service.transcribe_audio(tmp.name)
        self.assertEqual(result.text, "兜底文本")
        self.assertTrue(result.used_fallback)
        self.assertIn("primary_error", result.metadata)
        self.assertEqual(fallback.calls, [tmp.name])

    def test_without_fallback_raises(self):
        settings = RuntimeSettings(transcription_enabled=True, enable_baidu_fallback=False, keep_temp_files=True)
        service = TranscriptionService(settings, _PrimaryTranscriber(should_fail=True), None)
        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp, patch(
            "depression_detection.preprocessing.transcription.service.prepare_audio_for_transcription",
            return_value=Path(tmp.name),
        ):
            with self.assertRaises(TranscriptionError):
                service.transcribe_audio(tmp.name)

    def test_inline_audio_payload_is_written_then_transcribed(self):
        settings = RuntimeSettings(transcription_enabled=True, keep_temp_files=False, media_temp_dir=".cache/test-media")
        primary = _PrimaryTranscriber()
        service = TranscriptionService(settings, primary, None)

        def _prepared(audio_path: str, _settings: RuntimeSettings) -> Path:
            source = Path(audio_path)
            self.assertTrue(source.exists())
            self.assertEqual(source.suffix, ".webm")
            return source

        with patch(
            "depression_detection.preprocessing.transcription.service.prepare_audio_for_transcription",
            side_effect=_prepared,
        ):
            result = service.transcribe(AudioTranscriptionInput(audio_bytes=b"1234", filename="answer.webm", content_type="audio/webm"))

        self.assertEqual(result.text, "主路径文本")
        self.assertEqual(len(primary.calls), 1)
        self.assertEqual(Path(primary.calls[0]).suffix, ".webm")
        self.assertFalse(Path(primary.calls[0]).exists())

    def test_persisted_prepared_audio_path_overrides_temp_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = RuntimeSettings(transcription_enabled=True, keep_temp_files=False, media_temp_dir=temp_dir)
            primary = _PrimaryTranscriber()
            service = TranscriptionService(settings, primary, None)
            source = Path(temp_dir) / "capture.webm"
            source.write_bytes(b"video")
            prepared = Path(temp_dir) / "prepared.wav"
            prepared.write_bytes(b"audio")
            archived = Path(temp_dir) / "session" / "qa" / "q01" / "audio.wav"
            with patch(
                "depression_detection.preprocessing.transcription.service.prepare_audio_for_transcription",
                return_value=prepared,
            ):
                result = service.transcribe(
                    AudioTranscriptionInput(audio_path=str(source)),
                    prepared_audio_output_path=str(archived),
                )

            self.assertEqual(result.metadata["prepared_audio_path"], str(archived.resolve()))
            self.assertTrue(archived.exists())
            self.assertFalse(prepared.exists())


if __name__ == "__main__":
    unittest.main()
