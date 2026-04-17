import subprocess
from pathlib import Path
from uuid import uuid4

from depression_detection.config.settings import RuntimeSettings
from depression_detection.shared.exceptions import AudioPreparationError


def prepare_audio_for_transcription(audio_path: str, settings: RuntimeSettings) -> Path:
    source = Path(audio_path).expanduser().resolve()
    if not source.exists():
        raise AudioPreparationError(f"Audio path does not exist: {audio_path}")

    output_dir = Path(settings.media_temp_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{source.stem}-{uuid4().hex}.wav"
    command = [
        settings.ffmpeg_binary,
        "-y",
        "-i",
        str(source),
        "-ac",
        str(settings.audio_channels),
        "-ar",
        str(settings.audio_sample_rate),
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0 or not output_path.exists():
        raise AudioPreparationError(result.stderr.strip() or f"Failed to prepare audio for {audio_path}")
    return output_path
