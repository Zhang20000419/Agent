import unittest

from pydantic import ValidationError

from depression_detection.domain.enums import Modality, TaskType
from depression_detection.model.schemas import (
    MultimodalPredictionInput,
    PredictionResult,
    TextPredictionInput,
    VisionPredictionInput,
)


class ModelSchemasTests(unittest.TestCase):
    def test_text_prediction_input_defaults_to_text_modality(self):
        request = TextPredictionInput(sample_id="sample-1", task_type=TaskType.QA, text="情绪低落")
        self.assertEqual(request.modality, Modality.TEXT)

    def test_vision_prediction_requires_media(self):
        with self.assertRaises(ValidationError):
            VisionPredictionInput(sample_id="sample-1", task_type=TaskType.MOVIE)

    def test_multimodal_prediction_requires_at_least_one_payload(self):
        with self.assertRaises(ValidationError):
            MultimodalPredictionInput(sample_id="sample-1", task_type=TaskType.MOVIE)

    def test_prediction_result_score_range_is_validated(self):
        with self.assertRaises(ValidationError):
            PredictionResult(
                sample_id="sample-1",
                task_type=TaskType.QA,
                modality=Modality.TEXT,
                label="depression",
                score=1.5,
                confidence=0.8,
                evidence=[],
                auxiliary_outputs={},
                model_name="demo",
                model_version="v1",
            )


if __name__ == "__main__":
    unittest.main()
