import json
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from depression_detection.config.settings import RuntimeSettings
from depression_detection.tasks.interview.schemas import InterviewSessionState
from depression_detection.tasks.qa.question_bank import load_interview_questions


class ArchiveService:
    def __init__(self, settings: RuntimeSettings) -> None:
        self._settings = settings
        self._root = Path(settings.interview_archive_root).expanduser().resolve()

    @property
    def root(self) -> Path:
        self._root.mkdir(parents=True, exist_ok=True)
        return self._root

    def create_or_load_session(self, session_id: str | None = None) -> InterviewSessionState:
        session_id = session_id or self._generate_session_id()
        session_dir = self.root / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        session_path = session_dir / "session.json"
        if session_path.exists():
            return InterviewSessionState.model_validate(json.loads(session_path.read_text(encoding="utf-8")))

        now = self.now()
        questions = load_interview_questions()
        session = InterviewSessionState(
            session_id=session_id,
            created_at=now,
            updated_at=now,
            question_count=len(questions),
            questions=questions,
            stages={
                "movie": {},
                "reading": {},
                "qa": {},
            },
        )
        self.save_session(session)
        return session

    def load_session(self, session_id: str) -> InterviewSessionState:
        session_path = self.root / session_id / "session.json"
        return InterviewSessionState.model_validate(json.loads(session_path.read_text(encoding="utf-8")))

    def save_session(self, session: InterviewSessionState) -> InterviewSessionState:
        session.updated_at = self.now()
        session_dir = self.root / session.session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "session.json").write_text(
            json.dumps(session.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return session

    def item_dir(self, session_id: str, stage: str, item_key: str) -> Path:
        item_dir = self.root / session_id / stage / item_key
        item_dir.mkdir(parents=True, exist_ok=True)
        return item_dir

    def session_relative_path(self, session_id: str, path: str | Path) -> str:
        candidate = Path(path).expanduser().resolve()
        return str(candidate.relative_to((self.root / session_id).resolve()))

    def capture_path(self, session_id: str, stage: str, item_key: str, filename: str | None = None, content_type: str | None = None) -> Path:
        suffix = self._resolve_suffix(filename, content_type, default=".webm")
        return self.item_dir(session_id, stage, item_key) / f"capture{suffix}"

    def audio_path(self, session_id: str, stage: str, item_key: str) -> Path:
        return self.item_dir(session_id, stage, item_key) / "audio.wav"

    def transcript_path(self, session_id: str, stage: str, item_key: str) -> Path:
        return self.item_dir(session_id, stage, item_key) / "transcript.json"

    def diagnosis_path(self, session_id: str, stage: str, item_key: str) -> Path:
        return self.item_dir(session_id, stage, item_key) / "diagnosis.json"

    def write_bytes(self, path: str | Path, payload: bytes) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        return target

    def write_json(self, path: str | Path, payload: dict) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return target

    @staticmethod
    def qa_item_key(question_id: int) -> str:
        return f"q{question_id:02d}"

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _generate_session_id() -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return f"session-{timestamp}-{uuid4().hex[:8]}"

    @staticmethod
    def _resolve_suffix(filename: str | None, content_type: str | None, default: str) -> str:
        if filename:
            suffix = Path(filename).suffix.strip()
            if suffix:
                return suffix
        if content_type:
            guessed = mimetypes.guess_extension(content_type, strict=False)
            if guessed:
                return guessed
        return default
