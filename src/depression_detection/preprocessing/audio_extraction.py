import subprocess
from pathlib import Path
from uuid import uuid4

from depression_detection.config.settings import RuntimeSettings
from depression_detection.shared.exceptions import AudioPreparationError
from depression_detection.shared.logging import get_logger
from depression_detection.shared.tempfiles import FFMPEG_PREFIX, make_named_temp_file

logger = get_logger(__name__)


def prepare_audio_for_transcription(audio_path: str, settings: RuntimeSettings) -> Path:
    source = Path(audio_path).expanduser().resolve()
    if not source.exists():
        raise AudioPreparationError(f"Audio path does not exist: {audio_path}")

    output_path = make_named_temp_file(prefix=f"{FFMPEG_PREFIX}{source.stem}-{uuid4().hex}-", suffix=".wav")
    command = [
        settings.ffmpeg_binary,
        "-nostdin",
        "-y",
        "-i",
        str(source),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ac",
        str(settings.audio_channels),
        "-ar",
        str(settings.audio_sample_rate),
        str(output_path),
    ]
    logger.info("Running ffmpeg audio extraction: source=%s output=%s binary=%s", source, output_path, settings.ffmpeg_binary)
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            stdin=subprocess.DEVNULL,
            timeout=settings.ffmpeg_timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        logger.exception(
            "ffmpeg extraction timed out: source=%s output=%s timeout_seconds=%s",
            source,
            output_path,
            settings.ffmpeg_timeout_seconds,
            exc_info=exc,
        )
        raise AudioPreparationError(
            f"ffmpeg timed out after {settings.ffmpeg_timeout_seconds}s while processing {audio_path}"
        ) from exc

    stderr_text = (result.stderr or b"").decode("utf-8", errors="replace").strip()
    if result.returncode != 0 or not output_path.exists():
        logger.error(
            "ffmpeg extraction failed: source=%s output=%s returncode=%s stderr=%s",
            source,
            output_path,
            result.returncode,
            stderr_text,
        )
        raise AudioPreparationError(stderr_text or f"Failed to prepare audio for {audio_path}")
    logger.info("ffmpeg extraction finished: source=%s output=%s", source, output_path)
    return output_path
