import shutil
from pathlib import Path

from depression_detection.application.services.archive_service import ArchiveService
from depression_detection.config.settings import RuntimeSettings
from depression_detection.preprocessing.audio_extraction import prepare_audio_for_transcription
from depression_detection.preprocessing.schemas import AudioTranscriptionInput, TranscriptionResult
from depression_detection.shared.exceptions import TranscriptionError
from depression_detection.tasks.interview.assets import load_interview_asset_manifest
from depression_detection.tasks.interview.schemas import (
    DIAGNOSIS_PENDING_MODEL,
    DiagnosisEnvelope,
    InterviewSessionCreateResponse,
    InterviewSessionState,
    InterviewStageSubmissionResponse,
    MOVIE_READING_LABELS,
    StageArtifactRefs,
    StageRecord,
)
from depression_detection.tasks.qa.question_bank import get_question_index


class SessionWorkflowService:
    def __init__(
        self,
        archive_service: ArchiveService,
        qa_service,
        transcription_service,
        settings: RuntimeSettings,
    ) -> None:
        self._archive_service = archive_service
        self._qa_service = qa_service
        self._transcription_service = transcription_service
        self._settings = settings

    def create_session(self) -> InterviewSessionCreateResponse:
        session = self._archive_service.create_or_load_session()
        return InterviewSessionCreateResponse(session=session, assets=load_interview_asset_manifest())

    def get_session(self, session_id: str) -> InterviewSessionState:
        return self._archive_service.load_session(session_id)

    def submit_movie_capture(
        self,
        session_id: str,
        label: str,
        capture_bytes: bytes,
        filename: str | None,
        content_type: str | None,
    ) -> InterviewStageSubmissionResponse:
        self._validate_sentiment_label(label)
        return self._submit_capture(
            session_id=session_id,
            stage="movie",
            item_key=label,
            item_label=label,
            capture_bytes=capture_bytes,
            filename=filename,
            content_type=content_type,
            modality_plan=["vision"],
            extract_audio=False,
            transcribe=False,
            analyze_question_id=None,
        )

    def submit_reading_capture(
        self,
        session_id: str,
        label: str,
        capture_bytes: bytes,
        filename: str | None,
        content_type: str | None,
    ) -> InterviewStageSubmissionResponse:
        self._validate_sentiment_label(label)
        return self._submit_capture(
            session_id=session_id,
            stage="reading",
            item_key=label,
            item_label=label,
            capture_bytes=capture_bytes,
            filename=filename,
            content_type=content_type,
            modality_plan=["vision", "audio"],
            extract_audio=True,
            transcribe=False,
            analyze_question_id=None,
        )

    def submit_qa_capture(
        self,
        session_id: str,
        question_id: int,
        capture_bytes: bytes,
        filename: str | None,
        content_type: str | None,
    ) -> InterviewStageSubmissionResponse:
        if question_id not in get_question_index():
            raise ValueError("question_id not found")
        return self._submit_capture(
            session_id=session_id,
            stage="qa",
            item_key=self._archive_service.qa_item_key(question_id),
            item_label=f"question-{question_id}",
            capture_bytes=capture_bytes,
            filename=filename,
            content_type=content_type,
            modality_plan=["vision", "audio", "text"],
            extract_audio=True,
            transcribe=True,
            analyze_question_id=question_id,
        )

    def _submit_capture(
        self,
        session_id: str,
        stage: str,
        item_key: str,
        item_label: str,
        capture_bytes: bytes,
        filename: str | None,
        content_type: str | None,
        modality_plan: list[str],
        extract_audio: bool,
        transcribe: bool,
        analyze_question_id: int | None,
    ) -> InterviewStageSubmissionResponse:
        session = self._archive_service.load_session(session_id)
        capture_path = self._archive_service.capture_path(session.session_id, stage, item_key, filename, content_type)
        self._archive_service.write_bytes(capture_path, capture_bytes)

        audio_relpath: str | None = None
        transcript_relpath: str | None = None
        audio_path: Path | None = None
        transcript_result: TranscriptionResult | None = None
        diagnosis_payload: dict | None = None
        diagnosis_status = DIAGNOSIS_PENDING_MODEL
        diagnosis_error: str | None = None
        completed_at: str | None = None

        try:
            if extract_audio:
                audio_path = self._archive_service.audio_path(session.session_id, stage, item_key)
                if transcribe:
                    transcript_result = self._transcribe_capture_to_archive(capture_path, audio_path)
                else:
                    self._extract_audio_to_archive(capture_path, audio_path)
                audio_relpath = self._archive_service.session_relative_path(session.session_id, audio_path)

            if transcript_result is not None:
                transcript_path = self._archive_service.transcript_path(session.session_id, stage, item_key)
                normalized_transcript = self._normalize_transcription_result(
                    session.session_id,
                    transcript_result,
                    audio_relpath,
                )
                self._archive_service.write_json(transcript_path, normalized_transcript)
                transcript_relpath = self._archive_service.session_relative_path(session.session_id, transcript_path)

            if analyze_question_id is not None and transcript_result is not None:
                diagnosis_payload = self._qa_service.analyze_turn(analyze_question_id, transcript_result.text).model_dump(mode="json")
                diagnosis_status = "completed"
                completed_at = self._archive_service.now()
        except TranscriptionError as exc:
            diagnosis_status = "failed_preprocessing"
            diagnosis_error = str(exc)
        except Exception as exc:  # noqa: BLE001
            diagnosis_status = "failed_model"
            diagnosis_error = str(exc)

        diagnosis = DiagnosisEnvelope(
            status=diagnosis_status,
            modality_plan=modality_plan,
            requested_at=self._archive_service.now(),
            completed_at=completed_at,
            error=diagnosis_error,
            result=diagnosis_payload,
        )
        diagnosis_path = self._archive_service.diagnosis_path(session.session_id, stage, item_key)
        self._archive_service.write_json(diagnosis_path, diagnosis.model_dump(mode="json"))
        diagnosis_relpath = self._archive_service.session_relative_path(session.session_id, diagnosis_path)

        record = StageRecord(
            item_key=item_key,
            item_label=item_label,
            stage=stage,
            artifacts=StageArtifactRefs(
                capture=self._archive_service.session_relative_path(session.session_id, capture_path),
                audio=audio_relpath,
                transcript=transcript_relpath,
                diagnosis=diagnosis_relpath,
            ),
            diagnosis=diagnosis,
        )

        session.stages.setdefault(stage, {})[item_key] = record
        session = self._archive_service.save_session(session)
        return InterviewStageSubmissionResponse(session=session, record=record)

    def _extract_audio_to_archive(self, capture_path: Path, output_audio_path: Path) -> None:
        try:
            prepared_audio = prepare_audio_for_transcription(str(capture_path), self._settings)
        except Exception as exc:  # noqa: BLE001
            raise TranscriptionError(str(exc)) from exc
        output_audio_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(prepared_audio, output_audio_path)
        if not self._settings.keep_temp_files and prepared_audio.exists():
            prepared_audio.unlink()

    def _transcribe_capture_to_archive(self, capture_path: Path, output_audio_path: Path) -> TranscriptionResult:
        if self._transcription_service is None:
            raise TranscriptionError("transcription service is not available")
        return self._transcription_service.transcribe(
            AudioTranscriptionInput(audio_path=str(capture_path)),
            prepared_audio_output_path=str(output_audio_path),
        )

    def _normalize_transcription_result(
        self,
        session_id: str,
        result: TranscriptionResult,
        audio_relpath: str | None,
    ) -> dict:
        payload = result.model_dump(mode="json")
        metadata = dict(payload.get("metadata") or {})
        if audio_relpath:
            metadata["prepared_audio_path"] = audio_relpath
        payload["metadata"] = metadata
        return payload

    @staticmethod
    def _validate_sentiment_label(label: str) -> None:
        if label not in MOVIE_READING_LABELS:
            raise ValueError("label must be one of positive, neutral or negative")
