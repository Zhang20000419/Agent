import unittest

from depression_detection.domain.enums import Modality
from depression_detection.model.registry import ModelRegistry
from depression_detection.shared.exceptions import PredictorNotRegisteredError


class ModelRegistryTests(unittest.TestCase):
    def test_register_and_get_predictor(self):
        registry = ModelRegistry()
        predictor = object()
        registry.register(Modality.TEXT, predictor)
        self.assertIs(registry.get_text_predictor(), predictor)

    def test_missing_predictor_raises_clear_error(self):
        registry = ModelRegistry()
        with self.assertRaises(PredictorNotRegisteredError):
            registry.get_vision_predictor()


if __name__ == "__main__":
    unittest.main()
