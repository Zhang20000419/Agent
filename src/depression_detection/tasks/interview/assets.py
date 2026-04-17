from pathlib import Path

from depression_detection.config.settings import get_runtime_settings
from depression_detection.tasks.interview.schemas import InterviewAssetManifest, MovieAsset, MOVIE_READING_LABELS, ReadingAsset
from depression_detection.tasks.qa.schemas import InterviewQuestion


def get_interview_assets_root(question_dir: str | None = None) -> Path:
    configured_question_dir = Path(question_dir or get_runtime_settings().interview_question_dir).expanduser().resolve()
    if (configured_question_dir / "movie").exists() or (configured_question_dir / "reading").exists() or (configured_question_dir / "interview").exists():
        return configured_question_dir
    if configured_question_dir.name == "interview" or any(configured_question_dir.glob("*.txt")):
        return configured_question_dir.parent
    return configured_question_dir.parent


def load_question_assets(question_dir: str | None = None) -> list[InterviewQuestion]:
    configured_path = Path(question_dir or get_runtime_settings().interview_question_dir).expanduser().resolve()
    question_root = configured_path if configured_path.is_dir() and any(configured_path.glob("*.txt")) else get_interview_assets_root(question_dir) / "interview"
    question_files = sorted(question_root.glob("*.txt"), key=lambda path: int(path.stem))
    questions: list[InterviewQuestion] = []
    for path in question_files:
        question_text = path.read_text(encoding="utf-8").strip()
        if not question_text:
            continue
        questions.append(InterviewQuestion(question_id=int(path.stem), question_text=question_text))
    if not questions:
        raise RuntimeError(f"no interview question files found in {question_root}")
    return questions


def load_interview_asset_manifest(question_dir: str | None = None) -> InterviewAssetManifest:
    assets_root = get_interview_assets_root(question_dir)
    return InterviewAssetManifest(
        movie=[_load_movie_asset(assets_root, label) for label in MOVIE_READING_LABELS],
        reading=[_load_reading_asset(assets_root, label) for label in MOVIE_READING_LABELS],
        qa_questions=load_question_assets(question_dir),
    )


def _load_movie_asset(assets_root: Path, label: str) -> MovieAsset:
    asset_dir = assets_root / "movie" / label
    file_path = _first_file(asset_dir, allowed_suffixes={".mp4", ".mov", ".webm", ".m4v", ".avi"})
    return MovieAsset(
        key=label,
        title=f"{_zh_label(label)}电影",
        description=f"请播放{_zh_label(label)}电影素材，并录制受试者观看反应。",
        filename=file_path.name if file_path else None,
        url=f"/static/interview-assets/movie/{label}/{file_path.name}" if file_path else None,
    )


def _load_reading_asset(assets_root: Path, label: str) -> ReadingAsset:
    asset_dir = assets_root / "reading" / label
    file_path = _first_file(asset_dir, allowed_suffixes={".txt"})
    text = file_path.read_text(encoding="utf-8").strip() if file_path else ""
    return ReadingAsset(
        key=label,
        title=f"{_zh_label(label)}朗读",
        description=f"请朗读{_zh_label(label)}文字材料。",
        filename=file_path.name if file_path else None,
        text=text,
    )


def _first_file(asset_dir: Path, allowed_suffixes: set[str]) -> Path | None:
    if not asset_dir.exists():
        return None
    for path in sorted(asset_dir.iterdir()):
        if path.is_file() and path.name != ".gitkeep" and path.suffix.lower() in allowed_suffixes:
            return path
    return None


def _zh_label(label: str) -> str:
    return {
        "positive": "正性",
        "neutral": "中性",
        "negative": "负性",
    }.get(label, label)
