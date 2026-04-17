from collections import defaultdict
from typing import Any

from depression_detection.domain.enums import Modality
from depression_detection.shared.exceptions import PredictorNotRegisteredError


class ModelRegistry:
    def __init__(self) -> None:
        self._providers: dict[Modality, dict[str, Any]] = defaultdict(dict)

    def register(self, modality: Modality, predictor: Any, name: str = "default") -> None:
        self._providers[modality][name] = predictor

    def get(self, modality: Modality, name: str = "default") -> Any:
        try:
            return self._providers[modality][name]
        except KeyError as exc:
            raise PredictorNotRegisteredError(
                f"Predictor not registered for modality={modality} name={name}"
            ) from exc

    def get_text_predictor(self, name: str = "default") -> Any:
        return self.get(Modality.TEXT, name)

    def get_audio_predictor(self, name: str = "default") -> Any:
        return self.get(Modality.AUDIO, name)

    def get_vision_predictor(self, name: str = "default") -> Any:
        return self.get(Modality.VISION, name)

    def get_multimodal_predictor(self, name: str = "default") -> Any:
        return self.get(Modality.MULTIMODAL, name)
