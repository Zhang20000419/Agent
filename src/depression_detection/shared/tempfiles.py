import shutil
import tempfile
import time
from pathlib import Path

from depression_detection.shared.logging import get_logger

logger = get_logger(__name__)

TEMP_ROOT_NAME = "depression-detection-temp"
UPLOAD_PREFIX = "dd-upload-"
FFMPEG_PREFIX = "dd-ffmpeg-"
WHISPER_PREFIX = "dd-whisper-"
KNOWN_PREFIXES = (UPLOAD_PREFIX, FFMPEG_PREFIX, WHISPER_PREFIX)


def get_temp_root() -> Path:
    root = Path(tempfile.gettempdir()).expanduser().resolve() / TEMP_ROOT_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def make_named_temp_file(prefix: str, suffix: str) -> Path:
    handle = tempfile.NamedTemporaryFile(prefix=prefix, suffix=suffix, dir=str(get_temp_root()), delete=False)
    handle.close()
    return Path(handle.name).resolve()


def make_temp_dir(prefix: str) -> tempfile.TemporaryDirectory:
    return tempfile.TemporaryDirectory(prefix=prefix, dir=str(get_temp_root()))


def cleanup_stale_temp_artifacts(max_age_seconds: int) -> dict[str, int]:
    root = get_temp_root()
    now = time.time()
    removed_files = 0
    removed_dirs = 0
    errors = 0

    for entry in root.iterdir():
        if not entry.name.startswith(KNOWN_PREFIXES):
            continue
        age_seconds = now - entry.stat().st_mtime
        if age_seconds < max_age_seconds:
            continue
        try:
            if entry.is_dir():
                shutil.rmtree(entry, ignore_errors=False)
                removed_dirs += 1
            else:
                entry.unlink()
                removed_files += 1
        except FileNotFoundError:
            continue
        except Exception as exc:  # noqa: BLE001
            errors += 1
            logger.exception("Failed to cleanup stale temp artifact: path=%s", entry, exc_info=exc)

    if removed_files or removed_dirs or errors:
        logger.info(
            "Startup temp cleanup finished: root=%s removed_files=%s removed_dirs=%s errors=%s max_age_seconds=%s",
            root,
            removed_files,
            removed_dirs,
            errors,
            max_age_seconds,
        )
    return {
        "removed_files": removed_files,
        "removed_dirs": removed_dirs,
        "errors": errors,
    }
