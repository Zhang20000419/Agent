class DepressionDetectionError(Exception):
    """Base exception for the project."""


class PredictorNotRegisteredError(DepressionDetectionError):
    """Raised when a requested predictor has not been registered."""


class FeatureNotReadyError(DepressionDetectionError):
    """Raised when a planned modality/task is not implemented yet."""


class ModelLoadError(DepressionDetectionError):
    """Raised when a local model cannot be loaded."""


class AudioPreparationError(DepressionDetectionError):
    """Raised when audio cannot be prepared for transcription."""


class TranscriptionError(DepressionDetectionError):
    """Raised when audio transcription fails."""
