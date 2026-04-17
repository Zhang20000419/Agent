from dataclasses import dataclass
from email.parser import BytesParser
from email.policy import default

from fastapi import Request
from pydantic import ValidationError

from depression_detection.tasks.qa.schemas import TurnInput


@dataclass(frozen=True)
class ParsedTurnRequest:
    turn_input: TurnInput
    answer_audio_bytes: bytes | None = None


async def parse_turn_request(request: Request) -> ParsedTurnRequest:
    content_type = (request.headers.get("content-type") or "").lower()
    if content_type.startswith("application/json"):
        payload = await request.json()
        try:
            turn_input = TurnInput.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc
        return ParsedTurnRequest(turn_input=turn_input)
    if content_type.startswith("multipart/form-data"):
        return await _parse_multipart_turn_request(request)
    raise ValueError("unsupported content-type; use application/json or multipart/form-data")


async def _parse_multipart_turn_request(request: Request) -> ParsedTurnRequest:
    content_type = request.headers.get("content-type")
    if not content_type:
        raise ValueError("missing multipart content-type")

    body = await request.body()
    if not body:
        raise ValueError("multipart request body is empty")

    message = BytesParser(policy=default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
    )
    if not message.is_multipart():
        raise ValueError("multipart request body is invalid")

    fields: dict[str, str] = {}
    answer_audio_bytes: bytes | None = None
    answer_audio_filename: str | None = None
    answer_audio_content_type: str | None = None

    for part in message.iter_parts():
        field_name = part.get_param("name", header="content-disposition")
        if not field_name:
            continue

        payload = part.get_payload(decode=True) or b""
        filename = part.get_filename()
        is_file_field = filename is not None or field_name == "answer_audio"

        if is_file_field:
            if answer_audio_bytes is not None:
                raise ValueError("provide only one uploaded audio file")
            answer_audio_bytes = payload
            answer_audio_filename = filename
            answer_audio_content_type = part.get_content_type()
            continue

        fields[field_name] = _decode_text_part(part, payload)

    if answer_audio_bytes is not None and not answer_audio_bytes:
        raise ValueError("uploaded audio file is empty")

    try:
        turn_input = TurnInput.model_validate(
            {
                "question_id": fields.get("question_id"),
                "answer": fields.get("answer", ""),
                "answer_audio_base64": fields.get("answer_audio_base64"),
                "answer_audio_filename": fields.get("answer_audio_filename") or answer_audio_filename,
                "answer_audio_content_type": fields.get("answer_audio_content_type") or answer_audio_content_type,
                "answer_audio_path": fields.get("answer_audio_path"),
            }
        )
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc
    return ParsedTurnRequest(turn_input=turn_input, answer_audio_bytes=answer_audio_bytes)


def _decode_text_part(part, payload: bytes) -> str:
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset)
    except (LookupError, UnicodeDecodeError):
        return payload.decode("utf-8", errors="replace")
