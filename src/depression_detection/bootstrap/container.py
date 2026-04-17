from depression_detection.application.services.archive_service import ArchiveService
from depression_detection.application.services.debug_service import DebugServiceFacade
from depression_detection.application.services.interview_analysis_service import InterviewAnalysisService
from depression_detection.application.services.interview_service import InterviewServiceFacade
from depression_detection.application.services.movie_service import MovieServiceFacade
from depression_detection.application.services.prediction_service import PredictionServiceFacade
from depression_detection.application.services.qa_service import QAServiceFacade
from depression_detection.application.services.reading_service import ReadingServiceFacade
from depression_detection.application.services.session_workflow_service import SessionWorkflowService
from depression_detection.config.settings import RuntimeSettings, get_runtime_settings
from depression_detection.domain.enums import Modality
from depression_detection.model.providers.audio.local_audio_predictor import LocalAudioPredictor
from depression_detection.model.providers.multimodal.local_multimodal_predictor import LocalMultimodalPredictor
from depression_detection.model.providers.text.llm_text_predictor import LLMTextPredictor
from depression_detection.model.providers.text.local_text_predictor import LocalTextPredictor
from depression_detection.model.providers.vision.local_vision_predictor import LocalVisionPredictor
from depression_detection.model.registry import ModelRegistry
from depression_detection.preprocessing.transcription.baidu_asr_transcriber import BaiduAsrTranscriber
from depression_detection.preprocessing.transcription.service import TranscriptionService
from depression_detection.preprocessing.transcription.whisper_transcriber import WhisperTranscriber
from depression_detection.tasks.movie.service import MovieTaskService
from depression_detection.tasks.qa.service import QAAnalysisService
from depression_detection.tasks.reading.service import ReadingTaskService


class AppContainer:
    def __init__(self) -> None:
        self.settings = get_runtime_settings()
        self.registry = ModelRegistry()
        self._providers = self._register_predictors()
        self._archive_service = ArchiveService(self.settings)
        self._transcription_service = self._build_transcription_service()
        self._prediction_service = PredictionServiceFacade(self.registry)
        self._qa_service = QAServiceFacade(
            QAAnalysisService(
                text_runtime=self._providers["text_structured"],
                transcription_service=self._transcription_service,
                settings=self.settings,
            )
        )
        self._reading_service = ReadingServiceFacade(ReadingTaskService(self.registry, self.settings))
        self._movie_service = MovieServiceFacade(MovieTaskService(self.registry, self.settings))
        self._debug_service = DebugServiceFacade(self._transcription_service, self._qa_service)
        self._interview_analysis_service = InterviewAnalysisService(
            archive_service=self._archive_service,
            prediction_service=self._prediction_service,
            qa_service=self._qa_service,
            transcription_service=self._transcription_service,
            settings=self.settings,
        )
        self._interview_service = InterviewServiceFacade(
            SessionWorkflowService(
                archive_service=self._archive_service,
                prediction_service=self._prediction_service,
                interview_analysis_service=self._interview_analysis_service,
                settings=self.settings,
            )
        )

    def _register_predictors(self) -> dict[str, object]:
        llm_text = LLMTextPredictor()
        local_text = LocalTextPredictor()
        audio_default = LocalAudioPredictor()
        vision_default = LocalVisionPredictor()
        multimodal_default = LocalMultimodalPredictor()
        text_providers = {
            "llm": llm_text,
            "local": local_text,
        }
        audio_providers = {
            "local": audio_default,
        }
        vision_providers = {
            "local": vision_default,
        }
        multimodal_providers = {
            "local": multimodal_default,
        }

        self.registry.register(Modality.TEXT, llm_text, name="llm")
        self.registry.register(Modality.TEXT, local_text, name="local")
        self.registry.register(Modality.TEXT, llm_text, name="structured")
        self.registry.register(
            Modality.TEXT,
            text_providers.get(self.settings.text_provider, llm_text),
            name="default",
        )
        self.registry.register(Modality.AUDIO, audio_default, name="local")
        self.registry.register(
            Modality.AUDIO,
            audio_providers.get(self.settings.audio_provider, audio_default),
            name="default",
        )
        self.registry.register(Modality.VISION, vision_default, name="local")
        self.registry.register(
            Modality.VISION,
            vision_providers.get(self.settings.vision_provider, vision_default),
            name="default",
        )
        self.registry.register(Modality.MULTIMODAL, multimodal_default, name="local")
        self.registry.register(
            Modality.MULTIMODAL,
            multimodal_providers.get(self.settings.multimodal_provider, multimodal_default),
            name="default",
        )

        return {
            "text_structured": llm_text,
        }

    def _build_transcription_service(self) -> TranscriptionService | None:
        if not self.settings.transcription_enabled:
            return None
        primary = self._build_transcriber(self.settings.transcription_primary)
        fallback = None
        if self.settings.enable_baidu_fallback:
            fallback = self._build_transcriber(self.settings.transcription_fallback)
        return TranscriptionService(
            settings=self.settings,
            primary_transcriber=primary,
            fallback_transcriber=fallback,
        )

    def _build_transcriber(self, provider_name: str):
        normalized = (provider_name or "").strip().lower()
        if normalized in {"", "none"}:
            return None
        if normalized == "whisper":
            return WhisperTranscriber(self.settings)
        if normalized == "baidu":
            return BaiduAsrTranscriber(self.settings)
        raise ValueError(f"Unsupported transcription provider: {provider_name}")

    def qa_service(self) -> QAServiceFacade:
        return self._qa_service

    def reading_service(self) -> ReadingServiceFacade:
        return self._reading_service

    def movie_service(self) -> MovieServiceFacade:
        return self._movie_service

    def interview_service(self) -> InterviewServiceFacade:
        return self._interview_service

    def debug_service(self) -> DebugServiceFacade:
        return self._debug_service

    def prediction_service(self) -> PredictionServiceFacade:
        return self._prediction_service


_container: AppContainer | None = None


def get_container() -> AppContainer:
    global _container
    if _container is None:
        _container = AppContainer()
    return _container
