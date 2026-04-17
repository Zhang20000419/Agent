import base64
import socket
from pathlib import Path

import httpx

from depression_detection.config.settings import RuntimeSettings
from depression_detection.preprocessing.schemas import TranscriptionResult
from depression_detection.shared.exceptions import TranscriptionError


class BaiduAsrTranscriber:
    provider_name = "baidu"

    def __init__(self, settings: RuntimeSettings) -> None:
        self._settings = settings

    def _fetch_access_token(self) -> str:
        if not self._settings.baidu_asr_api_key or not self._settings.baidu_asr_secret_key:
            raise TranscriptionError("Missing Baidu ASR credentials")
        response = httpx.post(
            "https://aip.baidubce.com/oauth/2.0/token",
            params={
                "grant_type": "client_credentials",
                "client_id": self._settings.baidu_asr_api_key,
                "client_secret": self._settings.baidu_asr_secret_key,
            },
            timeout=self._settings.baidu_asr_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise TranscriptionError(f"Failed to get Baidu ASR token: {payload}")
        return token

    def transcribe(self, audio_path: str) -> TranscriptionResult:
        source = Path(audio_path).expanduser().resolve()
        if not source.exists():
            raise TranscriptionError(f"Audio path does not exist: {audio_path}")

        token = self._fetch_access_token()
        audio_bytes = source.read_bytes()
        response = httpx.post(
            "https://vop.baidu.com/server_api",
            json={
                "format": "wav",
                "rate": self._settings.audio_sample_rate,
                "channel": self._settings.audio_channels,
                "cuid": socket.gethostname(),
                "token": token,
                "speech": base64.b64encode(audio_bytes).decode("utf-8"),
                "len": len(audio_bytes),
                "dev_pid": 1537,
            },
            timeout=self._settings.baidu_asr_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("err_no") != 0 or not payload.get("result"):
            raise TranscriptionError(f"Baidu ASR failed: {payload}")
        text = str(payload["result"][0]).strip()
        if not text:
            raise TranscriptionError("Baidu ASR returned empty text")
        return TranscriptionResult(
            text=text,
            language=self._settings.transcription_language,
            provider=self.provider_name,
            metadata={"path": str(source), "payload": payload},
        )
