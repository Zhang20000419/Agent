import os
import subprocess
import time
import warnings


def _bootstrap_shell_env() -> None:
    # 兼容从 IDE 或非交互 shell 启动时拿不到 ~/.zshrc 里的环境变量。
    for name in [
        "LLM_PROVIDER",
        "ZHIPUAI_API_KEY",
        "ZHIPU_MODEL",
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
    try:
        result = subprocess.run(
            ["/bin/zsh", "-lic", f"printenv {name}"],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return None

    value = result.stdout.strip()
    return value or None


def _get_env(name: str) -> str | None:
    return os.getenv(name) or _read_shell_env(name)


def _build_gemini_model():
    from langchain_google_genai import ChatGoogleGenerativeAI

    api_key = _get_env("GEMINI_API_KEY") or _get_env("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("Missing GEMINI_API_KEY or GOOGLE_API_KEY.")

    model_name = _get_env("GEMINI_MODEL") or "gemini-2.5-flash-lite"
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0.1,
    )


def _build_zhipu_model():
    import httpx
    from langchain_community.chat_models import ChatZhipuAI
    from langchain_community.chat_models.zhipuai import (
        _get_jwt_token,
        _truncate_params,
    )
    from langchain_core.callbacks import CallbackManagerForLLMRun
    from langchain_core.language_models.chat_models import generate_from_stream
    from langchain_core.messages import BaseMessage
    from langchain_core.outputs import ChatResult

    warnings.filterwarnings(
        "ignore",
        message=r".*HMAC key is 16 bytes long.*",
    )

    api_key = _get_env("ZHIPUAI_API_KEY")
    if not api_key:
        raise EnvironmentError("Missing ZHIPUAI_API_KEY.")

    model_name = _get_env("ZHIPU_MODEL") or "glm-4-flash"

    # 社区版 ChatZhipuAI 把超时写死为 60 秒，这里做一个轻量包装，
    # 允许配置更长超时，并在免费额度下遇到 429 时自动退避重试。
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
                stream_iter = self._stream(
                    messages, stop=stop, run_manager=run_manager, **kwargs
                )
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

    request_timeout = float(_get_env("ZHIPU_TIMEOUT_SECONDS") or "180")
    max_retries_429 = int(_get_env("ZHIPU_MAX_RETRIES_429") or "3")
    retry_base_delay = float(_get_env("ZHIPU_RETRY_BASE_DELAY_SECONDS") or "6")
    return PatchedChatZhipuAI(
        api_key=api_key,
        model=model_name,
        temperature=0.1,
        request_timeout=request_timeout,
        max_retries_429=max_retries_429,
        retry_base_delay=retry_base_delay,
    )


def build_chat_model():
    # 每次构建模型前先把 shell 里的 provider、key、代理变量同步进当前进程。
    _bootstrap_shell_env()
    provider = (_get_env("LLM_PROVIDER") or "zhipu").strip().lower()

    if provider == "gemini":
        return _build_gemini_model()
    if provider == "zhipu":
        return _build_zhipu_model()

    raise ValueError("Unsupported LLM_PROVIDER. Use 'gemini' or 'zhipu'.")
