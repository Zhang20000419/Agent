from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class TaskType(StrEnum):
    QA = "qa"
    READING = "reading"
    MOVIE = "movie"
    INTERVIEW = "interview"


class Modality(StrEnum):
    TEXT = "text"
    AUDIO = "audio"
    VISION = "vision"
    MULTIMODAL = "multimodal"


class PredictionLabel(StrEnum):
    HEALTHY = "healthy"
    DEPRESSION = "depression"
    ANXIETY = "anxiety"
    BIPOLAR = "bipolar"
    UNCERTAIN = "uncertain"
