import shutil
import subprocess
import sys
from pathlib import Path

from depression_detection.config.settings import RuntimeSettings
from depression_detection.preprocessing.schemas import TranscriptionResult
from depression_detection.shared.exceptions import TranscriptionError


class WhisperTranscriber:
    provider_name = "whisper"

    def __init__(self, settings: RuntimeSettings) -> None:
        self._settings = settings

    def _build_command(self, binary: list[str], audio_path: Path, output_dir: Path) -> list[str]:
        return [
            *binary,
            str(audio_path),
            "--model",
            self._settings.whisper_model_name,
            "--language",
            self._settings.transcription_language,
            "--output_format",
            "txt",
            "--output_dir",
            str(output_dir),
            "--device",
            self._settings.whisper_device,
        ]

    def transcribe(self, audio_path: str) -> TranscriptionResult:
        source = Path(audio_path).expanduser().resolve()
        if not source.exists():
            raise TranscriptionError(f"Audio path does not exist: {audio_path}")

        output_dir = Path(self._settings.transcript_cache_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        txt_path = output_dir / f"{source.stem}.txt"

        candidates = []
        if shutil.which("whisper"):
            candidates.append(["whisper"])
        candidates.append([sys.executable, "-m", "whisper"])

        last_error = ""
        for binary in candidates:
            result = subprocess.run(
                self._build_command(binary, source, output_dir),
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0 and txt_path.exists():
                text = txt_path.read_text(encoding="utf-8").strip()
                if not text:
                    raise TranscriptionError("Whisper transcription produced empty text")
                return TranscriptionResult(
                    text=text,
                    language=self._settings.transcription_language,
                    provider=self.provider_name,
                    metadata={"path": str(source), "output": str(txt_path)},
                )
            last_error = result.stderr.strip() or result.stdout.strip()
        raise TranscriptionError(last_error or "Whisper transcription failed")
