import unittest

from depression_detection.config.settings import RuntimeSettings
from depression_detection.domain.enums import Modality, TaskType
from depression_detection.model.registry import ModelRegistry
from depression_detection.model.schemas import MultimodalPredictionInput
from depression_detection.tasks.movie.service import MovieTaskService


class MovieTaskServiceTests(unittest.TestCase):
    def test_movie_service_ignores_transcript_by_default(self):
        seen = {}

        class Predictor:
            def predict(self, request: MultimodalPredictionInput):
                seen["request"] = request
                return request

        registry = ModelRegistry()
        registry.register(Modality.MULTIMODAL, Predictor())
        service = MovieTaskService(registry, RuntimeSettings(movie_uses_text_modality=False))
        result = service.predict("sample-1", video_path="demo.mp4", image_paths=["frame.jpg"], transcript="字幕文本")
        self.assertEqual(result.task_type, TaskType.MOVIE)
        self.assertIsNone(result.text)

    def test_movie_service_keeps_transcript_when_explicitly_enabled(self):
        class Predictor:
            def predict(self, request: MultimodalPredictionInput):
                return request

        registry = ModelRegistry()
        registry.register(Modality.MULTIMODAL, Predictor())
        service = MovieTaskService(registry, RuntimeSettings(movie_uses_text_modality=True))
        result = service.predict("sample-1", video_path="demo.mp4", image_paths=["frame.jpg"], transcript="字幕文本")
        self.assertEqual(result.text, "字幕文本")


if __name__ == "__main__":
    unittest.main()
