import unittest

from depression_detection.domain.enums import Modality, PredictionLabel, TaskType
from depression_detection.model.schemas import (
    AudioPredictionInput,
    MultimodalPredictionInput,
    PredictionResult,
    TextPredictionInput,
    VisionPredictionInput,
)


class _TextPredictor:
    def predict(self, request: TextPredictionInput) -> PredictionResult:
        return PredictionResult(
            sample_id=request.sample_id,
            task_type=request.task_type,
            modality=request.modality,
            label=PredictionLabel.DEPRESSION,
            score=0.7,
            confidence=0.8,
            evidence=[request.text],
            auxiliary_outputs={},
            model_name="fake-text",
            model_version="v1",
        )


class _AudioPredictor:
    def predict(self, request: AudioPredictionInput) -> PredictionResult:
        return PredictionResult(
            sample_id=request.sample_id,
            task_type=request.task_type,
            modality=request.modality,
            label=PredictionLabel.ANXIETY,
            score=0.4,
            confidence=0.6,
            evidence=[request.audio_path],
            auxiliary_outputs={},
            model_name="fake-audio",
            model_version="v1",
        )


class _VisionPredictor:
    def predict(self, request: VisionPredictionInput) -> PredictionResult:
        return PredictionResult(
            sample_id=request.sample_id,
            task_type=request.task_type,
            modality=request.modality,
            label=PredictionLabel.HEALTHY,
            score=0.2,
            confidence=0.7,
            evidence=request.image_paths,
            auxiliary_outputs={},
            model_name="fake-vision",
            model_version="v1",
        )


class _MultimodalPredictor:
    def predict(self, request: MultimodalPredictionInput) -> PredictionResult:
        return PredictionResult(
            sample_id=request.sample_id,
            task_type=request.task_type,
            modality=request.modality,
            label=PredictionLabel.UNCERTAIN,
            score=0.5,
            confidence=0.5,
            evidence=[value for value in [request.text, request.video_path] if value],
            auxiliary_outputs={},
            model_name="fake-mm",
            model_version="v1",
        )


class PredictorContractTests(unittest.TestCase):
    def test_all_predictors_return_prediction_result(self):
        results = [
            _TextPredictor().predict(TextPredictionInput(sample_id="s1", task_type=TaskType.QA, text="情绪低落")),
            _AudioPredictor().predict(AudioPredictionInput(sample_id="s2", task_type=TaskType.READING, audio_path="demo.wav")),
            _VisionPredictor().predict(VisionPredictionInput(sample_id="s3", task_type=TaskType.MOVIE, image_paths=["frame.jpg"])),
            _MultimodalPredictor().predict(MultimodalPredictionInput(sample_id="s4", task_type=TaskType.MOVIE, text="字幕", video_path="demo.mp4")),
        ]
        self.assertEqual([result.modality for result in results], [Modality.TEXT, Modality.AUDIO, Modality.VISION, Modality.MULTIMODAL])
        self.assertTrue(all(isinstance(result, PredictionResult) for result in results))


if __name__ == "__main__":
    unittest.main()
