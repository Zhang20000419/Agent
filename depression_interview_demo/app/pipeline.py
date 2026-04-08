import json
import re
from functools import lru_cache

from langchain_core.output_parsers import PydanticOutputParser

from app.interview_questions import QUESTION_INDEX
from app.llm_config import build_chat_model
from app.prompts import EXTRACTOR_SYSTEM_PROMPT, REVIEWER_SYSTEM_PROMPT, SUMMARIZER_SYSTEM_PROMPT
from app.schemas import SessionAnalysis, TurnAnalysis


@lru_cache(maxsize=1)
def get_base_model():
    return build_chat_model()


@lru_cache(maxsize=1)
def get_turn_parser():
    return PydanticOutputParser(pydantic_object=TurnAnalysis)


@lru_cache(maxsize=1)
def get_session_parser():
    return PydanticOutputParser(pydantic_object=SessionAnalysis)


def _extract_content(response) -> str:
    content = response.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content)


def _clean_json_text(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    text = re.sub(r"//.*", "", text)
    return text.strip()


def _detect_language(text: str) -> str:
    chinese_count = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin_count = len(re.findall(r"[A-Za-z]", text))
    if chinese_count >= latin_count:
        return "zh"
    return "en"


def _language_instruction(language: str) -> str:
    if language == "en":
        return "输出语言要求：英文。所有可读文本字段必须使用英文。"
    return "输出语言要求：中文。所有可读文本字段必须使用中文。"


def _normalize_payload(payload: dict) -> dict:
    duration_map = {
        "more_than_2_weeks": "2_to_4_weeks",
        "two_to_four_weeks": "2_to_4_weeks",
        "2-4_weeks": "2_to_4_weeks",
        "2_4_weeks": "2_to_4_weeks",
        "less_than_two_weeks": "less_than_2_weeks",
        "one_to_three_months": "1_to_3_months",
        "more_than_three_months": "more_than_3_months",
        "unknown": "unclear",
    }
    frequency_map = {
        "every_day": "almost_every_day",
        "daily": "almost_every_day",
        "frequent": "often",
        "unknown": "unclear",
    }
    polarity_map = {
        "positive": "support",
        "negative": "deny",
    }

    if "duration" in payload and isinstance(payload["duration"], str):
        payload["duration"] = duration_map.get(payload["duration"], payload["duration"])
    if "frequency" in payload and isinstance(payload["frequency"], str):
        payload["frequency"] = frequency_map.get(payload["frequency"], payload["frequency"])
    if "polarity" in payload and isinstance(payload["polarity"], str):
        payload["polarity"] = polarity_map.get(payload["polarity"], payload["polarity"])
    return payload


def _invoke_structured(prompt: str, parser):
    response = get_base_model().invoke(prompt)
    text = _extract_content(response)
    try:
        return parser.parse(text)
    except Exception:
        cleaned = _clean_json_text(text)
        payload = _normalize_payload(json.loads(cleaned))
        return parser.pydantic_object.model_validate(payload)


def _normalize_turn_analysis(turn: TurnAnalysis) -> TurnAnalysis:
    turn.evidence = [item.strip() for item in turn.evidence if item and item.strip()]
    turn.explanation = turn.explanation.strip()
    turn.review_notes = turn.review_notes.strip()

    if not turn.evidence:
        turn.polarity = "uncertain"
        if turn.severity != "none":
            turn.severity = "mild"
        if turn.duration not in {"none", "unclear"}:
            turn.duration = "unclear"
            turn.duration_text = "不明确"
        if turn.frequency not in {"none", "unclear"}:
            turn.frequency = "unclear"
            turn.frequency_text = "不明确"
        turn.risk_flag = False
        turn.confidence = min(turn.confidence, 0.4)

    if turn.risk_flag and turn.severity != "none" and turn.polarity == "deny":
        turn.polarity = "support"
    if not turn.risk_flag and turn.severity == "none" and turn.polarity == "support":
        turn.polarity = "deny"

    if turn.polarity == "deny":
        turn.risk_flag = False
        if turn.severity != "none":
            turn.severity = "none"
    if turn.polarity == "uncertain":
        turn.risk_flag = False
        turn.confidence = min(turn.confidence, 0.5)

    if not turn.duration_text.strip():
        turn.duration_text = "不明确" if turn.duration == "unclear" else turn.duration
    if not turn.frequency_text.strip():
        turn.frequency_text = "不明确" if turn.frequency == "unclear" else turn.frequency
    if not turn.explanation:
        turn.explanation = "当前模型没有给出充分的可解释说明，因此该结果应谨慎使用。"

    turn.confidence = max(0.0, min(1.0, turn.confidence))
    return turn


def analyze_turn(question_id: int, answer: str) -> TurnAnalysis:
    question = QUESTION_INDEX[question_id]
    language = _detect_language(answer or question.question_text)
    turn_parser = get_turn_parser()
    extractor_prompt = (
        f"{EXTRACTOR_SYSTEM_PROMPT}\n\n"
        f"{_language_instruction(language)}\n\n"
        f"{turn_parser.get_format_instructions()}\n\n"
        f"question_id: {question.question_id}\n"
        f"question_text: {question.question_text}\n"
        f"answer: {answer}\n"
    )
    draft = _invoke_structured(extractor_prompt, turn_parser)

    reviewer_prompt = (
        f"{REVIEWER_SYSTEM_PROMPT}\n\n"
        f"{_language_instruction(language)}\n\n"
        f"{turn_parser.get_format_instructions()}\n\n"
        f"question_id: {question.question_id}\n"
        f"question_text: {question.question_text}\n"
        f"answer: {answer}\n"
        f"extractor_result: {json.dumps(draft.model_dump(mode='json'), ensure_ascii=False)}\n"
    )
    reviewed = _invoke_structured(reviewer_prompt, turn_parser)
    reviewed.question_id = question.question_id
    reviewed.question_text = question.question_text
    reviewed.answer = answer
    return _normalize_turn_analysis(reviewed)


def analyze_session(session_id: str, responses: list[dict]) -> SessionAnalysis:
    turns = [analyze_turn(item["question_id"], item["answer"]) for item in responses]
    language = _detect_language(" ".join(item["answer"] for item in responses if item.get("answer")))
    session_parser = get_session_parser()
    summarizer_prompt = (
        f"{SUMMARIZER_SYSTEM_PROMPT}\n\n"
        f"{_language_instruction(language)}\n\n"
        f"{session_parser.get_format_instructions()}\n\n"
        f"session_id: {session_id}\n"
        f"turns: {json.dumps([turn.model_dump(mode='json') for turn in turns], ensure_ascii=False)}\n"
    )
    result = _invoke_structured(summarizer_prompt, session_parser)
    result.session_id = session_id
    result.turns = turns
    return result
