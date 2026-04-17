from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock

from depression_detection.application.services.archive_service import ArchiveService
from depression_detection.application.services.prediction_service import PredictionServiceFacade
from depression_detection.config.settings import RuntimeSettings
from depression_detection.domain.enums import Modality, PredictionLabel, TaskType
from depression_detection.model.schemas import AudioPredictionInput, MultimodalPredictionInput, PredictionResult, VisionPredictionInput
from depression_detection.preprocessing.schemas import AudioTranscriptionInput
from depression_detection.shared.exceptions import TranscriptionError
from depression_detection.shared.logging import get_logger
from depression_detection.tasks.interview.schemas import DiagnosisEnvelope


class InterviewAnalysisService:
    def __init__(
        self,
        archive_service: ArchiveService,
        prediction_service: PredictionServiceFacade,
        qa_service,
        transcription_service,
        settings: RuntimeSettings,
    ) -> None:
        self._archive_service = archive_service
        self._prediction_service = prediction_service
        self._qa_service = qa_service
        self._transcription_service = transcription_service
        self._settings = settings
        self._executor = ThreadPoolExecutor(max_workers=max(settings.interview_analysis_workers, 1), thread_name_prefix="interview-analysis")
        self._lock = Lock()
        self._logger = get_logger(__name__)

    def enqueue_qa_analysis(self, session_id: str, question_id: int) -> None:
        self._logger.info("Submitting async QA analysis task: session=%s question_id=%s", session_id, question_id)
        self._executor.submit(self._run_qa_analysis, session_id, question_id)

    def build_stage_placeholder_result(self, sample_id: str, task_type: TaskType, modality: Modality, evidence_path: str, analysis: str) -> PredictionResult:
        if modality == Modality.VISION:
            return self._prediction_service.predict_vision(
                VisionPredictionInput(
                    sample_id=sample_id,
                    task_type=task_type,
                    video_path=evidence_path,
                    metadata={"placeholder_analysis": analysis},
                )
            )
        if modality == Modality.AUDIO:
            return self._prediction_service.predict_audio(
                AudioPredictionInput(
                    sample_id=sample_id,
                    task_type=task_type,
                    audio_path=evidence_path,
                    metadata={"placeholder_analysis": analysis},
                )
            )
        raise ValueError(f"unsupported placeholder modality: {modality}")

    def _run_qa_analysis(self, session_id: str, question_id: int) -> None:
        self._logger.info("Async QA analysis started: session=%s question_id=%s", session_id, question_id)
        with self._lock:
            session = self._archive_service.load_session(session_id)
            item_key = self._archive_service.qa_item_key(question_id)
            record = session.stages.setdefault("qa", {}).get(item_key)
            if record is None:
                return

            record.diagnosis = DiagnosisEnvelope(
                status="processing",
                modality_plan=["vision", "audio", "text"],
                requested_at=record.diagnosis.requested_at,
                completed_at=None,
                error=None,
                result=None,
            )
            session.analysis_summary.status = "processing"
            self._archive_service.save_session(session)

        try:
            session = self._archive_service.load_session(session_id)
            record = session.stages["qa"][item_key]
            capture_path = (self._archive_service.root / session_id / record.artifacts.capture).resolve()
            audio_path = self._archive_service.audio_path(session_id, "qa", item_key)
            transcript_result = self._transcription_service.transcribe(
                AudioTranscriptionInput(audio_path=str(capture_path)),
                prepared_audio_output_path=str(audio_path),
            )
            self._logger.info("Transcript ready: session=%s question_id=%s provider=%s fallback=%s", session_id, question_id, transcript_result.provider, transcript_result.used_fallback)
            audio_relpath = self._archive_service.session_relative_path(session_id, audio_path)
            transcript_path = self._archive_service.transcript_path(session_id, "qa", item_key)
            normalized_transcript = self._normalize_transcription_result(transcript_result, audio_relpath)
            self._archive_service.write_json(transcript_path, normalized_transcript)
            transcript_relpath = self._archive_service.session_relative_path(session_id, transcript_path)

            turn_analysis = self._qa_service.analyze_turn(question_id, transcript_result.text).model_dump(mode="json")
            completed_at = self._archive_service.now()

            session = self._archive_service.load_session(session_id)
            record = session.stages["qa"][item_key]
            record.artifacts.audio = audio_relpath
            record.artifacts.transcript = transcript_relpath
            record.diagnosis = DiagnosisEnvelope(
                status="completed",
                modality_plan=["vision", "audio", "text"],
                requested_at=record.diagnosis.requested_at,
                completed_at=completed_at,
                error=None,
                result={
                    "transcript": transcript_result.text,
                    "transcript_provider": transcript_result.provider,
                    "transcript_used_fallback": transcript_result.used_fallback,
                    "transcript_confidence": transcript_result.confidence,
                    "turn_analysis": turn_analysis,
                },
            )
            self._archive_service.write_json(
                self._archive_service.diagnosis_path(session_id, "qa", item_key),
                record.diagnosis.model_dump(mode="json"),
            )
            self._archive_service.save_session(session)
            self._logger.info("Async QA analysis completed for turn: session=%s question_id=%s", session_id, question_id)
            self._refresh_interview_summary(session_id)
        except Exception as exc:  # noqa: BLE001
            self._logger.exception("Async QA analysis failed: session=%s question_id=%s", session_id, question_id, exc_info=exc)
            session = self._archive_service.load_session(session_id)
            record = session.stages["qa"][item_key]
            record.diagnosis = DiagnosisEnvelope(
                status="failed_preprocessing" if isinstance(exc, TranscriptionError) else "failed_model",
                modality_plan=["vision", "audio", "text"],
                requested_at=record.diagnosis.requested_at,
                completed_at=None,
                error=str(exc),
                result=None,
            )
            self._archive_service.write_json(
                self._archive_service.diagnosis_path(session_id, "qa", item_key),
                record.diagnosis.model_dump(mode="json"),
            )
            session.analysis_summary.status = "failed_model"
            session.analysis_summary.error = str(exc)
            self._archive_service.save_session(session)

    def _refresh_interview_summary(self, session_id: str) -> None:
        with self._lock:
            session = self._archive_service.load_session(session_id)
            qa_records = session.stages.get("qa", {})
            total_questions = session.question_count
            completed_records = [
                record
                for record in qa_records.values()
                if record.diagnosis.status == "completed" and record.diagnosis.result and record.diagnosis.result.get("turn_analysis")
            ]
            if len(completed_records) < total_questions:
                session.analysis_summary.status = "processing"
                self._archive_service.save_session(session)
                self._logger.info("Interview summary still waiting: session=%s completed=%s total=%s", session_id, len(completed_records), total_questions)
                return

            completed_records.sort(key=lambda item: int(item.item_key.lstrip("q")))
            turns = [record.diagnosis.result["turn_analysis"] for record in completed_records]
            text_session_analysis = self._qa_service.summarize_session_from_turns(session_id, turns).model_dump(mode="json")
            text_result = self._build_text_prediction(session_id, text_session_analysis)
            vision_result = self.build_stage_placeholder_result(
                sample_id=session_id,
                task_type=TaskType.INTERVIEW,
                modality=Modality.VISION,
                evidence_path=self._first_capture_reference(session, "movie"),
                analysis="当前版本暂未启用视觉抑郁识别模型，因此视觉模态返回默认占位结果。",
            )
            audio_result = self.build_stage_placeholder_result(
                sample_id=session_id,
                task_type=TaskType.INTERVIEW,
                modality=Modality.AUDIO,
                evidence_path=self._first_audio_reference(session),
                analysis="当前版本暂未启用音频抑郁识别模型，因此音频模态返回默认占位结果。",
            )
            multimodal_result = self._prediction_service.predict_multimodal(
                MultimodalPredictionInput(
                    sample_id=session_id,
                    task_type=TaskType.INTERVIEW,
                    text=text_result.analysis,
                    audio_path=self._first_audio_reference(session),
                    video_path=self._first_capture_reference(session, "movie"),
                    metadata={
                        "modality_results": {
                            "vision": vision_result.model_dump(mode="json"),
                            "audio": audio_result.model_dump(mode="json"),
                            "text": text_result.model_dump(mode="json"),
                        }
                    },
                )
            )
            session.analysis_summary.status = "completed"
            session.analysis_summary.completed_at = self._archive_service.now()
            session.analysis_summary.error = None
            session.analysis_summary.vision = vision_result
            session.analysis_summary.audio = audio_result
            session.analysis_summary.text = text_result
            session.analysis_summary.multimodal = multimodal_result
            session.analysis_summary.text_session_analysis = text_session_analysis
            self._archive_service.save_session(session)
            self._logger.info("Interview summary completed: session=%s label=%s", session_id, multimodal_result.label)

    @staticmethod
    def _normalize_transcription_result(result, audio_relpath: str | None) -> dict:
        payload = result.model_dump(mode="json")
        metadata = dict(payload.get("metadata") or {})
        if audio_relpath:
            metadata["prepared_audio_path"] = audio_relpath
        payload["metadata"] = metadata
        return payload

    @staticmethod
    def _map_label(session_analysis: dict) -> PredictionLabel:
        classifications = session_analysis.get("session_classification") or []
        for item in classifications:
            try:
                return PredictionLabel(item)
            except ValueError:
                continue
        return PredictionLabel.UNCERTAIN

    def _build_text_prediction(self, session_id: str, session_analysis: dict) -> PredictionResult:
        label = self._map_label(session_analysis)
        confidence = float(session_analysis.get("overall_confidence") or 0.0)
        score = confidence if label != PredictionLabel.HEALTHY else max(0.0, 1.0 - confidence)
        return PredictionResult(
            sample_id=session_id,
            task_type=TaskType.INTERVIEW,
            modality=Modality.TEXT,
            label=label,
            score=max(0.0, min(1.0, score)),
            confidence=max(0.0, min(1.0, confidence)),
            evidence=list(session_analysis.get("key_findings") or []),
            analysis=session_analysis.get("explanation") or session_analysis.get("summary") or "文本模态已完成分析。",
            auxiliary_outputs={"session_analysis": session_analysis},
            model_name="QAAnalysisService",
            model_version="qa-text-session-v1",
        )

    @staticmethod
    def _first_capture_reference(session, preferred_stage: str) -> str:
        for stage_name in [preferred_stage, "reading", "qa"]:
            stage_records = session.stages.get(stage_name, {})
            for record in stage_records.values():
                if record.artifacts.capture:
                    return record.artifacts.capture
        return "placeholder-video.webm"

    @staticmethod
    def _first_audio_reference(session) -> str:
        for stage_name in ["qa", "reading"]:
            stage_records = session.stages.get(stage_name, {})
            for record in stage_records.values():
                if record.artifacts.audio:
                    return record.artifacts.audio
        return "placeholder-audio.wav"
