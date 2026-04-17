import mimetypes
import shutil
from pathlib import Path
from uuid import uuid4

from depression_detection.config.settings import RuntimeSettings
from depression_detection.preprocessing.audio_extraction import prepare_audio_for_transcription
from depression_detection.preprocessing.schemas import AudioTranscriptionInput, TranscriptionResult
from depression_detection.shared.exceptions import TranscriptionError
from depression_detection.shared.logging import get_logger
from depression_detection.shared.tempfiles import UPLOAD_PREFIX, make_named_temp_file

logger = get_logger(__name__)


class TranscriptionService:
    def __init__(
        self,
        settings: RuntimeSettings,
        primary_transcriber,
        fallback_transcriber=None,
    ) -> None:
        self._settings = settings
        self._primary = primary_transcriber
        self._fallback = fallback_transcriber

    def transcribe_audio(self, audio_path: str) -> TranscriptionResult:
        return self.transcribe(AudioTranscriptionInput(audio_path=audio_path))

    def transcribe(self, request: AudioTranscriptionInput, prepared_audio_output_path: str | None = None) -> TranscriptionResult:
        source_path: Path | None = None
        prepared_audio: Path | None = None
        cleanup_source = False
        if request.audio_bytes is not None:
            source_path = self._persist_audio_bytes(request.audio_bytes, request.filename, request.content_type)
            cleanup_source = True
        elif request.audio_path:
            source_path = Path(request.audio_path)
        else:
            raise TranscriptionError("audio source is required for transcription")

        try:
            prepared_audio = prepare_audio_for_transcription(str(source_path), self._settings)
        except Exception as preparation_error:
            logger.exception("Audio preparation failed for transcription: source=%s", source_path, exc_info=preparation_error)
            raise TranscriptionError(str(preparation_error)) from preparation_error

        persisted_prepared_audio: Path | None = None
        if prepared_audio_output_path:
            persisted_prepared_audio = Path(prepared_audio_output_path).expanduser().resolve()
            persisted_prepared_audio.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(prepared_audio, persisted_prepared_audio)

        try:
            logger.info("Transcription primary start: provider=%s audio=%s", getattr(self._primary, "provider_name", type(self._primary).__name__), prepared_audio)
            result = self._primary.transcribe(str(prepared_audio))
            result.metadata["prepared_audio_path"] = str(persisted_prepared_audio or prepared_audio)
            logger.info("Transcription primary success: provider=%s audio=%s", result.provider, prepared_audio)
            return result
        except Exception as primary_error:
            if not self._settings.enable_baidu_fallback or self._fallback is None:
                logger.exception("Transcription primary failed without fallback: audio=%s", prepared_audio, exc_info=primary_error)
                raise TranscriptionError(str(primary_error)) from primary_error
            logger.warning("Transcription primary failed, switching to fallback: audio=%s error=%s", prepared_audio, primary_error)
            fallback_result = self._fallback.transcribe(str(prepared_audio))
            fallback_result.used_fallback = True
            fallback_result.metadata["prepared_audio_path"] = str(persisted_prepared_audio or prepared_audio)
            fallback_result.metadata["primary_error"] = str(primary_error)
            logger.info("Transcription fallback success: provider=%s audio=%s", fallback_result.provider, prepared_audio)
            return fallback_result
        finally:
            if cleanup_source and source_path is not None and source_path.exists():
                source_path.unlink()
            if prepared_audio is not None and not self._settings.keep_temp_files:
                prepared_path = Path(prepared_audio)
                if prepared_path.exists():
                    prepared_path.unlink()

    def _persist_audio_bytes(self, audio_bytes: bytes, filename: str | None, content_type: str | None) -> Path:
        suffix = self._resolve_suffix(filename, content_type)
        source_path = make_named_temp_file(prefix=f"{UPLOAD_PREFIX}{uuid4().hex}-", suffix=suffix)
        source_path.write_bytes(audio_bytes)
        return source_path

    @staticmethod
    def _resolve_suffix(filename: str | None, content_type: str | None) -> str:
        if filename:
            suffix = Path(filename).suffix.strip()
            if suffix:
                return suffix
        if content_type:
            guessed = mimetypes.guess_extension(content_type, strict=False)
            if guessed:
                return guessed
        return ".wav"
