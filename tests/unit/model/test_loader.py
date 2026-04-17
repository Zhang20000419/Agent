import tempfile
import unittest
from pathlib import Path

from depression_detection.model.loader import ModelLoader
from depression_detection.shared.exceptions import ModelLoadError


class ModelLoaderTests(unittest.TestCase):
    def test_loader_caches_same_key(self):
        loader = ModelLoader()
        calls = []

        def factory():
            calls.append("called")
            return {"model": "demo"}

        first = loader.load("text:default", factory)
        second = loader.load("text:default", factory)
        self.assertIs(first, second)
        self.assertEqual(len(calls), 1)

    def test_loader_raises_for_missing_model_path(self):
        loader = ModelLoader()
        missing = Path(tempfile.gettempdir()) / "missing-demo-model.bin"
        with self.assertRaises(ModelLoadError):
            loader.load("text:local", lambda: object(), model_path=str(missing))


if __name__ == "__main__":
    unittest.main()
