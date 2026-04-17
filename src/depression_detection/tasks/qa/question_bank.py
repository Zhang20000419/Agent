from pathlib import Path

from depression_detection.tasks.interview.assets import get_interview_assets_root, load_question_assets
from depression_detection.tasks.qa.schemas import InterviewQuestion


def get_question_bank_dir(question_dir: str | None = None) -> Path:
    return get_interview_assets_root(question_dir) / "interview"


def load_interview_questions(question_dir: str | None = None) -> list[InterviewQuestion]:
    return load_question_assets(question_dir)


def get_question_index(question_dir: str | None = None) -> dict[int, InterviewQuestion]:
    return {item.question_id: item for item in load_interview_questions(question_dir)}
