import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from depression_detection.config.settings import RuntimeSettings
from depression_detection.preprocessing.transcription.baidu_asr_transcriber import BaiduAsrTranscriber


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class BaiduAsrTranscriberTests(unittest.TestCase):
    def test_baidu_transcriber_returns_text(self):
        settings = RuntimeSettings(
            baidu_asr_api_key="key",
            baidu_asr_secret_key="secret",
        )
        transcriber = BaiduAsrTranscriber(settings)
        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp, patch(
            "depression_detection.preprocessing.transcription.baidu_asr_transcriber.httpx.post",
            side_effect=[
                _Response({"access_token": "token"}),
                _Response({"err_no": 0, "result": ["百度转写文本"]}),
            ],
        ):
            result = transcriber.transcribe(tmp.name)

        self.assertEqual(result.text, "百度转写文本")
        self.assertEqual(result.provider, "baidu")


if __name__ == "__main__":
    unittest.main()
