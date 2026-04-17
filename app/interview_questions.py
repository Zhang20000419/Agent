from depression_detection.tasks.qa.question_bank import get_question_index, load_interview_questions


def __getattr__(name: str):
    if name == "INTERVIEW_QUESTIONS":
        return load_interview_questions()
    if name == "QUESTION_INDEX":
        return get_question_index()
    raise AttributeError(name)


__all__ = ["INTERVIEW_QUESTIONS", "QUESTION_INDEX", "load_interview_questions", "get_question_index"]
