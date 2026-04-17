import os
import subprocess
import time
import warnings
from functools import lru_cache

from pydantic import BaseModel, Field


class RuntimeSettings(BaseModel):
    app_name: str = Field(default="Mental Interview Demo")
    version: str = Field(default="0.1.0")
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8090)

    current_stage: str = Field(default="qa")
    qa_text_enabled: bool = Field(default=True)
    qa_audio_transcription_enabled: bool = Field(default=True)
    allow_local_audio_path_input: bool = Field(default=True)
    movie_uses_text_modality: bool = Field(default=False)
    reading_uses_text_modality: bool = Field(default=False)

    llm_provider: str = Field(default="zhipu")
    text_provider: str = Field(default="llm")
    audio_provider: str = Field(default="local")
    vision_provider: str = Field(default="local")
    multimodal_provider: str = Field(default="local")
    local_model_root: str = Field(default="models")
    device: str = Field(default="cpu")

    transcription_enabled: bool = Field(default=True)
    transcription_primary: str = Field(default="whisper")
    transcription_fallback: str = Field(default="baidu")
    enable_baidu_fallback: bool = Field(default=True)
    transcription_language: str = Field(default="zh")

    whisper_model_name: str = Field(default="base")
    whisper_device: str = Field(default="cpu")

    baidu_asr_app_id: str = Field(default="")
    baidu_asr_api_key: str = Field(default="")
    baidu_asr_secret_key: str = Field(default="")
    baidu_asr_timeout_seconds: int = Field(default=30)

    ffmpeg_binary: str = Field(default="ffmpeg")
    audio_sample_rate: int = Field(default=16000)
    audio_channels: int = Field(default=1)
    interview_question_dir: str = Field(default="app/static/interview-assets/interview")
    interview_archive_root: str = Field(default=".cache/interviews")
    media_temp_dir: str = Field(default=".cache/media")
    transcript_cache_dir: str = Field(default=".cache/transcripts")
    keep_temp_files: bool = Field(default=False)

    zhipu_api_key: str = Field(default="")
    zhipu_model: str = Field(default="glm-4-flash")
    zhipu_timeout_seconds: float = Field(default=180.0)
    zhipu_max_retries_429: int = Field(default=3)
    zhipu_retry_base_delay_seconds: float = Field(default=6.0)

    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-2.5-flash-lite")

    @classmethod
    def from_env(cls) -> "RuntimeSettings":
        _bootstrap_shell_env()
        gemini_api_key = _get_env("GEMINI_API_KEY") or _get_env("GOOGLE_API_KEY") or ""
        return cls(
            app_name=_get_env("APP_NAME") or "Mental Interview Demo",
            version=_get_env("APP_VERSION") or "0.1.0",
            host=_get_env("APP_HOST") or "127.0.0.1",
            port=int(_get_env("APP_PORT") or "8090"),
            current_stage=(_get_env("CURRENT_STAGE") or "qa").strip().lower(),
            qa_text_enabled=_get_bool_env("QA_TEXT_ENABLED", True),
            qa_audio_transcription_enabled=_get_bool_env("QA_AUDIO_TRANSCRIPTION_ENABLED", True),
            allow_local_audio_path_input=_get_bool_env("ALLOW_LOCAL_AUDIO_PATH_INPUT", True),
            movie_uses_text_modality=_get_bool_env("MOVIE_USES_TEXT_MODALITY", False),
            reading_uses_text_modality=_get_bool_env("READING_USES_TEXT_MODALITY", False),
            llm_provider=(_get_env("LLM_PROVIDER") or "zhipu").strip().lower(),
            text_provider=(_get_env("TEXT_MODEL_PROVIDER") or "llm").strip().lower(),
            audio_provider=(_get_env("AUDIO_MODEL_PROVIDER") or "local").strip().lower(),
            vision_provider=(_get_env("VISION_MODEL_PROVIDER") or "local").strip().lower(),
            multimodal_provider=(_get_env("MULTIMODAL_MODEL_PROVIDER") or "local").strip().lower(),
            local_model_root=_get_env("LOCAL_MODEL_ROOT") or "models",
            device=(_get_env("MODEL_DEVICE") or "cpu").strip().lower(),
            transcription_enabled=_get_bool_env("TRANSCRIPTION_ENABLED", True),
            transcription_primary=(_get_env("TRANSCRIPTION_PRIMARY") or "whisper").strip().lower(),
            transcription_fallback=(_get_env("TRANSCRIPTION_FALLBACK") or "baidu").strip().lower(),
            enable_baidu_fallback=_get_bool_env("ENABLE_BAIDU_FALLBACK", True),
            transcription_language=(_get_env("TRANSCRIPTION_LANGUAGE") or "zh").strip().lower(),
            whisper_model_name=_get_env("WHISPER_MODEL_NAME") or "base",
            whisper_device=(_get_env("WHISPER_DEVICE") or (_get_env("MODEL_DEVICE") or "cpu")).strip().lower(),
            baidu_asr_app_id=_get_env("BAIDU_ASR_APP_ID") or "",
            baidu_asr_api_key=_get_env("BAIDU_ASR_API_KEY") or "",
            baidu_asr_secret_key=_get_env("BAIDU_ASR_SECRET_KEY") or "",
            baidu_asr_timeout_seconds=int(_get_env("BAIDU_ASR_TIMEOUT_SECONDS") or "30"),
            ffmpeg_binary=_get_env("FFMPEG_BINARY") or "ffmpeg",
            audio_sample_rate=int(_get_env("AUDIO_SAMPLE_RATE") or "16000"),
            audio_channels=int(_get_env("AUDIO_CHANNELS") or "1"),
            interview_question_dir=_get_env("INTERVIEW_QUESTION_DIR") or "app/static/interview-assets/interview",
            interview_archive_root=_get_env("INTERVIEW_ARCHIVE_ROOT") or ".cache/interviews",
            media_temp_dir=_get_env("MEDIA_TEMP_DIR") or ".cache/media",
            transcript_cache_dir=_get_env("TRANSCRIPT_CACHE_DIR") or ".cache/transcripts",
            keep_temp_files=_get_bool_env("KEEP_TEMP_FILES", False),
            zhipu_api_key=_get_env("ZHIPUAI_API_KEY") or "",
            zhipu_model=_get_env("ZHIPU_MODEL") or "glm-4-flash",
            zhipu_timeout_seconds=float(_get_env("ZHIPU_TIMEOUT_SECONDS") or "180"),
            zhipu_max_retries_429=int(_get_env("ZHIPU_MAX_RETRIES_429") or "3"),
            zhipu_retry_base_delay_seconds=float(_get_env("ZHIPU_RETRY_BASE_DELAY_SECONDS") or "6"),
            gemini_api_key=gemini_api_key,
            gemini_model=_get_env("GEMINI_MODEL") or "gemini-2.5-flash-lite",
        )


def _bootstrap_shell_env() -> None:
    for name in [
        "APP_NAME",
        "APP_VERSION",
        "APP_HOST",
        "APP_PORT",
        "CURRENT_STAGE",
        "QA_TEXT_ENABLED",
        "QA_AUDIO_TRANSCRIPTION_ENABLED",
        "ALLOW_LOCAL_AUDIO_PATH_INPUT",
        "MOVIE_USES_TEXT_MODALITY",
        "READING_USES_TEXT_MODALITY",
        "LLM_PROVIDER",
        "TEXT_MODEL_PROVIDER",
        "AUDIO_MODEL_PROVIDER",
        "VISION_MODEL_PROVIDER",
        "MULTIMODAL_MODEL_PROVIDER",
        "LOCAL_MODEL_ROOT",
        "MODEL_DEVICE",
        "TRANSCRIPTION_ENABLED",
        "TRANSCRIPTION_PRIMARY",
        "TRANSCRIPTION_FALLBACK",
        "ENABLE_BAIDU_FALLBACK",
        "TRANSCRIPTION_LANGUAGE",
        "WHISPER_MODEL_NAME",
        "WHISPER_DEVICE",
        "BAIDU_ASR_APP_ID",
        "BAIDU_ASR_API_KEY",
        "BAIDU_ASR_SECRET_KEY",
        "BAIDU_ASR_TIMEOUT_SECONDS",
        "FFMPEG_BINARY",
        "AUDIO_SAMPLE_RATE",
        "AUDIO_CHANNELS",
        "INTERVIEW_QUESTION_DIR",
        "INTERVIEW_ARCHIVE_ROOT",
        "MEDIA_TEMP_DIR",
        "TRANSCRIPT_CACHE_DIR",
        "KEEP_TEMP_FILES",
        "ZHIPUAI_API_KEY",
        "ZHIPU_MODEL",
        "ZHIPU_TIMEOUT_SECONDS",
        "ZHIPU_MAX_RETRIES_429",
        "ZHIPU_RETRY_BASE_DELAY_SECONDS",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_MODEL",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
    ]:
        if os.getenv(name):
            continue
        value = _read_shell_env(name)
        if value:
            os.environ[name] = value


def _read_shell_env(name: str) -> str | None:
    return _read_shell_env_map().get(name)


@lru_cache(maxsize=1)
def _read_shell_env_map() -> dict[str, str]:
    try:
        result = subprocess.run(
            ["/bin/zsh", "-lic", "env"],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return {}

    values: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if "=" not in line:
            continue
        env_name, env_value = line.split("=", 1)
        values[env_name] = env_value
    return values


def _get_env(name: str) -> str | None:
    return os.getenv(name) or _read_shell_env(name)


def _get_bool_env(name: str, default: bool) -> bool:
    value = _get_env(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache(maxsize=1)
def get_runtime_settings() -> RuntimeSettings:
    return RuntimeSettings.from_env()


def _build_gemini_model():
    from langchain_google_genai import ChatGoogleGenerativeAI

    settings = get_runtime_settings()
    if not settings.gemini_api_key:
        raise EnvironmentError("Missing GEMINI_API_KEY or GOOGLE_API_KEY.")

    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.1,
    )


def _build_zhipu_model():
    import httpx
    from langchain_community.chat_models import ChatZhipuAI
    from langchain_community.chat_models.zhipuai import _get_jwt_token, _truncate_params
    from langchain_core.callbacks import CallbackManagerForLLMRun
    from langchain_core.language_models.chat_models import generate_from_stream
    from langchain_core.messages import BaseMessage
    from langchain_core.outputs import ChatResult

    settings = get_runtime_settings()
    warnings.filterwarnings(
        "ignore",
        message=r".*HMAC key is 16 bytes long.*",
    )

    if not settings.zhipu_api_key:
        raise EnvironmentError("Missing ZHIPUAI_API_KEY.")

    class PatchedChatZhipuAI(ChatZhipuAI):
        request_timeout: float = 180.0
        max_retries_429: int = 3
        retry_base_delay: float = 6.0

        def _generate(
            self,
            messages: list[BaseMessage],
            stop: list[str] | None = None,
            run_manager: CallbackManagerForLLMRun | None = None,
            stream: bool | None = None,
            **kwargs,
        ) -> ChatResult:
            should_stream = stream if stream is not None else self.streaming
            if should_stream:
                stream_iter = self._stream(messages, stop=stop, run_manager=run_manager, **kwargs)
                return generate_from_stream(stream_iter)

            if self.zhipuai_api_key is None:
                raise ValueError("Did not find zhipuai_api_key.")
            message_dicts, params = self._create_message_dicts(messages, stop)
            payload = {**params, **kwargs, "messages": message_dicts, "stream": False}
            _truncate_params(payload)
            headers = {
                "Authorization": _get_jwt_token(self.zhipuai_api_key),
                "Accept": "application/json",
            }
            with httpx.Client(headers=headers, timeout=self.request_timeout) as client:
                for attempt in range(self.max_retries_429 + 1):
                    response = client.post(self.zhipuai_api_base, json=payload)
                    if response.status_code != 429:
                        response.raise_for_status()
                        return self._create_chat_result(response.json())

                    if attempt >= self.max_retries_429:
                        response.raise_for_status()

                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else self.retry_base_delay * (attempt + 1)
                    time.sleep(delay)

            raise RuntimeError("Zhipu request retry loop ended unexpectedly.")

    return PatchedChatZhipuAI(
        api_key=settings.zhipu_api_key,
        model=settings.zhipu_model,
        temperature=0.1,
        request_timeout=settings.zhipu_timeout_seconds,
        max_retries_429=settings.zhipu_max_retries_429,
        retry_base_delay=settings.zhipu_retry_base_delay_seconds,
    )


def build_chat_model():
    settings = get_runtime_settings()
    if settings.llm_provider == "gemini":
        return _build_gemini_model()
    if settings.llm_provider == "zhipu":
        return _build_zhipu_model()
    raise ValueError("Unsupported LLM_PROVIDER. Use 'gemini' or 'zhipu'.")
