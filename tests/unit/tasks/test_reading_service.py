import unittest

from depression_detection.config.settings import RuntimeSettings
from depression_detection.domain.enums import Modality, TaskType
from depression_detection.model.registry import ModelRegistry
from depression_detection.model.schemas import AudioPredictionInput
from depression_detection.shared.exceptions import FeatureNotReadyError
from depression_detection.tasks.reading.service import ReadingTaskService


class _FailingAudioPredictor:
    def predict(self, request: AudioPredictionInput):
        raise FeatureNotReadyError("audio not ready")


class ReadingTaskServiceTests(unittest.TestCase):
    def test_reading_service_builds_audio_request(self):
        seen = {}

        class Predictor:
            def predict(self, request: AudioPredictionInput):
                seen["request"] = request
                return request

        registry = ModelRegistry()
        registry.register(Modality.AUDIO, Predictor())
        service = ReadingTaskService(registry, RuntimeSettings(reading_uses_text_modality=False))
        result = service.predict("sample-1", "demo.wav", "你好")
        self.assertEqual(result.task_type, TaskType.READING)
        self.assertIsNone(result.transcript)

    def test_reading_service_keeps_transcript_only_when_enabled(self):
        seen = {}

        class Predictor:
            def predict(self, request: AudioPredictionInput):
                seen["request"] = request
                return request

        registry = ModelRegistry()
        registry.register(Modality.AUDIO, Predictor())
        service = ReadingTaskService(registry, RuntimeSettings(reading_uses_text_modality=True))
        result = service.predict("sample-1", "demo.wav", "你好")
        self.assertEqual(result.transcript, "你好")

    def test_reading_service_surfaces_feature_not_ready(self):
        registry = ModelRegistry()
        registry.register(Modality.AUDIO, _FailingAudioPredictor())
        service = ReadingTaskService(registry, RuntimeSettings())
        with self.assertRaises(FeatureNotReadyError):
            service.predict("sample-1", "demo.wav")


if __name__ == "__main__":
    unittest.main()
