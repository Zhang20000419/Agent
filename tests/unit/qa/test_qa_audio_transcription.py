import unittest
from unittest.mock import patch

from depression_detection.config.settings import RuntimeSettings
from depression_detection.preprocessing.schemas import AudioTranscriptionInput, TranscriptionResult
from depression_detection.tasks.qa.service import QAAnalysisService


class _DummyTextRuntime:
    def invoke(self, prompt: str):
        raise AssertionError(f"unexpected model call: {prompt}")


class _TranscriptionService:
    def __init__(self):
        self.calls: list[AudioTranscriptionInput] = []

    def transcribe(self, request: AudioTranscriptionInput) -> TranscriptionResult:
        self.calls.append(request)
        return TranscriptionResult(text="转写后的回答", language="zh", provider="whisper")


class QAAudioTranscriptionTests(unittest.TestCase):
    def test_resolve_answer_prefers_direct_text(self):
        service = QAAnalysisService(text_runtime=_DummyTextRuntime(), transcription_service=_TranscriptionService(), settings=RuntimeSettings())
        self.assertEqual(service._resolve_answer("直接文本", "ignored.wav"), "直接文本")

    def test_resolve_answer_uses_transcription_when_answer_missing(self):
        transcriber = _TranscriptionService()
        service = QAAnalysisService(text_runtime=_DummyTextRuntime(), transcription_service=transcriber, settings=RuntimeSettings())
        answer = service._resolve_answer("", "demo.wav")
        self.assertEqual(answer, "转写后的回答")
        self.assertEqual(transcriber.calls, [AudioTranscriptionInput(audio_path="demo.wav")])

    def test_resolve_answer_supports_base64_audio_payload(self):
        transcriber = _TranscriptionService()
        service = QAAnalysisService(text_runtime=_DummyTextRuntime(), transcription_service=transcriber, settings=RuntimeSettings())
        answer = service._resolve_answer("", None, "aGVsbG8=", "demo.wav", "audio/wav")
        self.assertEqual(answer, "转写后的回答")
        self.assertEqual(
            transcriber.calls,
            [AudioTranscriptionInput(audio_bytes=b"hello", filename="demo.wav", content_type="audio/wav")],
        )

    def test_resolve_answer_supports_uploaded_audio_bytes(self):
        transcriber = _TranscriptionService()
        service = QAAnalysisService(text_runtime=_DummyTextRuntime(), transcription_service=transcriber, settings=RuntimeSettings())
        answer = service._resolve_answer("", None, None, "demo.wav", "audio/wav", b"hello")
        self.assertEqual(answer, "转写后的回答")
        self.assertEqual(
            transcriber.calls,
            [AudioTranscriptionInput(audio_bytes=b"hello", filename="demo.wav", content_type="audio/wav")],
        )

    def test_resolve_answer_rejects_invalid_base64_payload(self):
        service = QAAnalysisService(text_runtime=_DummyTextRuntime(), transcription_service=_TranscriptionService(), settings=RuntimeSettings())
        with self.assertRaisesRegex(ValueError, "answer_audio_base64 is not valid"):
            service._resolve_answer("", None, "%%%")

    def test_resolve_answer_rejects_local_audio_path_when_disabled(self):
        transcriber = _TranscriptionService()
        settings = RuntimeSettings(allow_local_audio_path_input=False)
        service = QAAnalysisService(text_runtime=_DummyTextRuntime(), transcription_service=transcriber, settings=settings)
        with self.assertRaisesRegex(ValueError, "answer_audio_path is disabled"):
            service._resolve_answer("", "demo.wav")
        self.assertEqual(transcriber.calls, [])

    def test_analyze_session_passes_audio_path_to_analyze_turn(self):
        service = QAAnalysisService(text_runtime=_DummyTextRuntime(), transcription_service=_TranscriptionService(), settings=RuntimeSettings())
        fake_turn = object()
        with patch.object(service, "analyze_turn", return_value=fake_turn) as analyze_turn_mock:
            turns = service._build_turns_from_responses([
                {"question_id": 1, "answer": "", "answer_audio_base64": "aGVsbG8=", "answer_audio_filename": "demo.wav"}
            ])
        analyze_turn_mock.assert_called_once_with(1, "", None, "aGVsbG8=", "demo.wav", None, None)
        self.assertEqual(turns, [fake_turn])


if __name__ == "__main__":
    unittest.main()
