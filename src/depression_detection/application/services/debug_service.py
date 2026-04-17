from depression_detection.preprocessing.schemas import AudioTranscriptionInput
from depression_detection.shared.exceptions import TranscriptionError


class DebugServiceFacade:
    def __init__(self, transcription_service, qa_service) -> None:
        self._transcription_service = transcription_service
        self._qa_service = qa_service

    def check_qa_chain(self, question_id: int, capture_bytes: bytes, filename: str | None = None, content_type: str | None = None) -> dict:
        result = {
            "success": False,
            "question_id": question_id,
            "filename": filename,
            "content_type": content_type,
            "size_bytes": len(capture_bytes),
            "transcription": None,
            "turn_analysis": None,
            "error_stage": None,
            "error": None,
        }

        if self._transcription_service is None:
            result["error_stage"] = "transcription"
            result["error"] = "transcription service is not available"
            return result

        try:
            transcription = self._transcription_service.transcribe(
                AudioTranscriptionInput(
                    audio_bytes=capture_bytes,
                    filename=filename,
                    content_type=content_type,
                )
            )
            result["transcription"] = transcription.model_dump(mode="json")
        except TranscriptionError as exc:
            result["error_stage"] = "transcription"
            result["error"] = str(exc)
            return result

        try:
            turn_analysis = self._qa_service.analyze_turn(question_id, transcription.text)
            result["turn_analysis"] = turn_analysis.model_dump(mode="json")
            result["success"] = True
            return result
        except Exception as exc:  # noqa: BLE001
            result["error_stage"] = "analysis"
            result["error"] = str(exc)
            return result
