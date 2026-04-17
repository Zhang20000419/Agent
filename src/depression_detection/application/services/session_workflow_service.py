import shutil
from pathlib import Path

from depression_detection.application.services.archive_service import ArchiveService
from depression_detection.config.settings import RuntimeSettings
from depression_detection.domain.enums import Modality, TaskType
from depression_detection.preprocessing.audio_extraction import prepare_audio_for_transcription
from depression_detection.shared.exceptions import TranscriptionError
from depression_detection.shared.logging import get_logger
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
        prediction_service,
        interview_analysis_service,
        settings: RuntimeSettings,
    ) -> None:
        self._archive_service = archive_service
        self._prediction_service = prediction_service
        self._interview_analysis_service = interview_analysis_service
        self._settings = settings
        self._logger = get_logger(__name__)

    def create_session(self) -> InterviewSessionCreateResponse:
        session = self._archive_service.create_or_load_session()
        self._logger.info("Created interview session %s", session.session_id)
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
            placeholder_analysis="当前看电影阶段暂不进行抑郁识别分析，已完成视频归档。",
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
            extract_audio=False,
            placeholder_analysis="当前朗读阶段暂不进行抑郁识别分析，已完成视频归档并返回占位音频结果。",
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
            extract_audio=False,
            placeholder_analysis=None,
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
        placeholder_analysis: str | None,
        analyze_question_id: int | None,
    ) -> InterviewStageSubmissionResponse:
        self._logger.info("Persisting capture: session=%s stage=%s item=%s filename=%s content_type=%s", session_id, stage, item_key, filename, content_type)
        session = self._archive_service.load_session(session_id)
        capture_path = self._archive_service.capture_path(session.session_id, stage, item_key, filename, content_type)
        self._archive_service.write_bytes(capture_path, capture_bytes)

        audio_relpath: str | None = None
        diagnosis_payload: dict | None = None
        diagnosis_status = DIAGNOSIS_PENDING_MODEL
        diagnosis_error: str | None = None
        completed_at: str | None = None

        try:
            if extract_audio:
                audio_path = self._archive_service.audio_path(session.session_id, stage, item_key)
                self._logger.info("Extracting audio: session=%s stage=%s item=%s capture=%s audio=%s", session_id, stage, item_key, capture_path, audio_path)
                self._extract_audio_to_archive(capture_path, audio_path)
                audio_relpath = self._archive_service.session_relative_path(session.session_id, audio_path)

            if analyze_question_id is None and placeholder_analysis:
                diagnosis_payload = self._build_placeholder_payload(
                    session.session_id,
                    stage,
                    capture_path,
                    audio_relpath,
                    placeholder_analysis,
                )
                diagnosis_status = "completed"
                completed_at = self._archive_service.now()
            elif analyze_question_id is not None:
                diagnosis_status = "queued"
                self._logger.info("Queued async QA analysis: session=%s question_id=%s", session_id, analyze_question_id)
        except TranscriptionError as exc:
            self._logger.exception("Preprocessing failed: session=%s stage=%s item=%s", session_id, stage, item_key, exc_info=exc)
            diagnosis_status = "failed_preprocessing"
            diagnosis_error = str(exc)
        except Exception as exc:  # noqa: BLE001
            self._logger.exception("Model/storage flow failed: session=%s stage=%s item=%s", session_id, stage, item_key, exc_info=exc)
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
                transcript=None,
                diagnosis=diagnosis_relpath,
            ),
            diagnosis=diagnosis,
        )

        session.stages.setdefault(stage, {})[item_key] = record
        if analyze_question_id is not None and diagnosis_status == "queued":
            session.analysis_summary.status = "processing"
        session = self._archive_service.save_session(session)
        if analyze_question_id is not None and diagnosis_status == "queued":
            self._interview_analysis_service.enqueue_qa_analysis(session.session_id, analyze_question_id)
        return InterviewStageSubmissionResponse(session=session, record=record)

    def _extract_audio_to_archive(self, capture_path: Path, output_audio_path: Path) -> None:
        try:
            prepared_audio = prepare_audio_for_transcription(str(capture_path), self._settings)
        except Exception as exc:  # noqa: BLE001
            raise TranscriptionError(str(exc)) from exc
        output_audio_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(prepared_audio, output_audio_path)
        self._logger.info("Audio extracted: capture=%s prepared=%s archived=%s", capture_path, prepared_audio, output_audio_path)
        if not self._settings.keep_temp_files and prepared_audio.exists():
            prepared_audio.unlink()

    def _build_placeholder_payload(
        self,
        session_id: str,
        stage: str,
        capture_path: Path,
        audio_relpath: str | None,
        analysis: str,
    ) -> dict:
        if stage == "movie":
            result = self._interview_analysis_service.build_stage_placeholder_result(
                sample_id=session_id,
                task_type=TaskType.MOVIE,
                modality=Modality.VISION,
                evidence_path=self._archive_service.session_relative_path(session_id, capture_path),
                analysis=analysis,
            )
        else:
            result = self._interview_analysis_service.build_stage_placeholder_result(
                sample_id=session_id,
                task_type=TaskType.READING,
                modality=Modality.AUDIO,
                evidence_path=audio_relpath or self._archive_service.session_relative_path(session_id, capture_path),
                analysis=analysis,
            )
        return result.model_dump(mode="json")

    @staticmethod
    def _validate_sentiment_label(label: str) -> None:
        if label not in MOVIE_READING_LABELS:
            raise ValueError("label must be one of positive, neutral or negative")
