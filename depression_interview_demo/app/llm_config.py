import os
import warnings


def _build_gemini_model():
    from langchain_google_genai import ChatGoogleGenerativeAI

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("Missing GEMINI_API_KEY or GOOGLE_API_KEY.")

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0.1,
    )


def _build_zhipu_model():
    from langchain_community.chat_models import ChatZhipuAI

    warnings.filterwarnings(
        "ignore",
        message=r".*HMAC key is 16 bytes long.*",
    )

    api_key = os.getenv("ZHIPUAI_API_KEY")
    if not api_key:
        raise EnvironmentError("Missing ZHIPUAI_API_KEY.")

    model_name = os.getenv("ZHIPU_MODEL", "GLM-4.7-Flash")
    return ChatZhipuAI(
        api_key=api_key,
        model=model_name,
        temperature=0.1,
    )


def build_chat_model():
    provider = os.getenv("LLM_PROVIDER", "zhipu").strip().lower()

    if provider == "gemini":
        return _build_gemini_model()
    if provider == "zhipu":
        return _build_zhipu_model()

    raise ValueError("Unsupported LLM_PROVIDER. Use 'gemini' or 'zhipu'.")
