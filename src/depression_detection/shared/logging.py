import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from depression_detection.config.settings import RuntimeSettings


_CONFIGURED = False


def configure_interview_logging(settings: RuntimeSettings) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_dir = Path(settings.interview_log_dir).expanduser().resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "interview-backend.log"

    formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    file_handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
