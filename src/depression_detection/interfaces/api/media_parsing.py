from dataclasses import dataclass
from email.parser import BytesParser
from email.policy import default

from fastapi import Request


@dataclass(frozen=True)
class UploadedMedia:
    filename: str | None
    content_type: str | None
    data: bytes
    fields: dict[str, str]


async def parse_uploaded_media(request: Request, file_field: str = "capture") -> UploadedMedia:
    content_type = request.headers.get("content-type") or ""
    if not content_type.lower().startswith("multipart/form-data"):
        raise ValueError("unsupported content-type; use multipart/form-data for media upload")

    body = await request.body()
    if not body:
        raise ValueError("multipart request body is empty")

    message = BytesParser(policy=default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
    )
    if not message.is_multipart():
        raise ValueError("multipart request body is invalid")

    fields: dict[str, str] = {}
    uploaded_filename: str | None = None
    uploaded_type: str | None = None
    uploaded_data: bytes | None = None

    for part in message.iter_parts():
        field_name = part.get_param("name", header="content-disposition")
        if not field_name:
            continue
        payload = part.get_payload(decode=True) or b""
        if part.get_filename() is not None or field_name == file_field:
            if field_name != file_field:
                continue
            if uploaded_data is not None:
                raise ValueError("provide only one uploaded capture file")
            uploaded_filename = part.get_filename()
            uploaded_type = part.get_content_type()
            uploaded_data = payload
            continue
        charset = part.get_content_charset() or "utf-8"
        try:
            fields[field_name] = payload.decode(charset)
        except (LookupError, UnicodeDecodeError):
            fields[field_name] = payload.decode("utf-8", errors="replace")

    if uploaded_data is None:
        raise ValueError(f"missing `{file_field}` upload")
    if not uploaded_data:
        raise ValueError("uploaded capture file is empty")
    return UploadedMedia(filename=uploaded_filename, content_type=uploaded_type, data=uploaded_data, fields=fields)
