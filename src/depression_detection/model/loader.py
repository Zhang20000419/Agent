from pathlib import Path
from typing import Any, Callable

from depression_detection.shared.exceptions import ModelLoadError


class ModelLoader:
    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}

    def load(self, cache_key: str, factory: Callable[[], Any], model_path: str | None = None) -> Any:
        if cache_key in self._cache:
            return self._cache[cache_key]
        if model_path:
            path = Path(model_path).expanduser()
            if not path.exists():
                raise ModelLoadError(f"Model path does not exist: {model_path}")
        model = factory()
        self._cache[cache_key] = model
        return model

    def get(self, cache_key: str) -> Any | None:
        return self._cache.get(cache_key)

    def clear(self) -> None:
        self._cache.clear()
