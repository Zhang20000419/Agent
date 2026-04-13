import json
import re
from functools import lru_cache

from langchain_core.output_parsers import PydanticOutputParser

from app.interview_questions import QUESTION_INDEX
from app.llm_config import build_chat_model
from app.prompts import EXTRACTOR_SYSTEM_PROMPT, REVIEWER_SYSTEM_PROMPT, REVIEW_DECISION_SYSTEM_PROMPT, SUMMARIZER_SYSTEM_PROMPT
from app.schemas import ReviewDecision, SessionAnalysis, SessionSummary, TurnAnalysis


@lru_cache(maxsize=1)
def get_base_model():
    # 模型实例按进程缓存，避免每次请求都重复初始化。
    return build_chat_model()


@lru_cache(maxsize=1)
def get_turn_parser():
    return PydanticOutputParser(pydantic_object=TurnAnalysis)


@lru_cache(maxsize=1)
def get_session_parser():
    return PydanticOutputParser(pydantic_object=SessionSummary)


@lru_cache(maxsize=1)
def get_review_decision_parser():
    return PydanticOutputParser(pydantic_object=ReviewDecision)


def _extract_content(response) -> str:
    # 兼容不同 LangChain 模型返回的 content 形态：纯字符串或富文本块列表。
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
    # 清理模型常见输出噪声，提升二次 JSON 解析成功率。
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    text = re.sub(r"//.*", "", text)
    return text.strip()


def _detect_language(text: str) -> str:
    # 输出语言跟随输入语言，减少中英混杂。
    chinese_count = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin_count = len(re.findall(r"[A-Za-z]", text))
    if chinese_count >= latin_count:
        return "zh"
    return "en"


def _language_instruction(language: str) -> str:
    if language == "en":
        return "输出语言要求：英文。所有可读文本字段必须使用英文。"
    return "输出语言要求：中文。所有可读文本字段必须使用中文。"


def _enum_text_map(language: str) -> dict[str, str]:
    if language != "zh":
        return {}
    return {
        "less_than_2_weeks": "少于两周",
        "2_to_4_weeks": "两到四周",
        "1_to_3_months": "一到三个月",
        "more_than_3_months": "三个月以上",
        "almost_every_day": "几乎每天",
        "sometimes": "有时",
        "often": "经常",
        "rare": "很少",
        "unclear": "不明确",
        "none": "无",
        "mild": "轻度",
        "moderate": "中度",
        "severe": "重度",
        "support": "支持症状存在",
        "deny": "否定症状存在",
        "uncertain": "信息不足",
        "depression": "抑郁",
        "bipolar": "双相",
        "anxiety": "焦虑",
        "healthy": "健康",
        "overall_risk": "整体风险",
        "session_classification": "访谈分类",
        "question_id": "题号",
        "question_text": "题目文本",
        "duration": "持续时间",
        "duration_text": "持续时间说明",
        "frequency": "频率",
        "frequency_text": "频率说明",
        "severity": "严重程度",
        "polarity": "极性",
        "confidence": "置信度",
        "evidence": "证据",
        "explanation": "解释说明",
        "review_notes": "复核说明",
        "risk_flag": "风险标记",
    }


def _localize_text(text: str, language: str) -> str:
    if language != "zh" or not text:
        return text
    localized = text
    for source, target in sorted(_enum_text_map(language).items(), key=lambda item: len(item[0]), reverse=True):
        localized = re.sub(rf"(?<![A-Za-z0-9_]){re.escape(source)}(?![A-Za-z0-9_])", target, localized)
    return localized.strip()


def _localize_text_list(items: list[str], language: str) -> list[str]:
    return [_localize_text(item.strip(), language) for item in items if item and item.strip()]


def _normalize_payload(payload: dict) -> dict:
    # 对模型常见的近似枚举做归一化，减少因为拼写偏差导致的校验失败。
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


def _normalize_duration_from_text(duration_text: str, duration_value: str) -> str:
    # 如果模型给出的枚举与文本片段不一致，以文本证据为准做保守纠偏。
    text = duration_text.strip().lower()
    if not text:
        return duration_value

    if re.search(r"(一天|1天|两天|2天|几天|数天)", text):
        return "less_than_2_weeks"
    if re.search(r"(一周|1周|两周|2周|十天|10天|十二天|12天)", text):
        return "less_than_2_weeks"
    if re.search(r"(三周|3周|四周|4周|一个月内|近一个月)", text):
        return "2_to_4_weeks"
    if re.search(r"(一个月|1个月|两个月|2个月|三个月内|3个月内)", text):
        return "1_to_3_months"
    if re.search(r"(三个月以上|3个月以上|半年|几个月|数月|长期)", text):
        return "more_than_3_months"
    return duration_value


def _normalize_frequency_from_text(frequency_text: str, frequency_value: str) -> str:
    text = frequency_text.strip().lower()
    if not text:
        return frequency_value

    if re.search(r"(没有|无|从不)", text):
        return "none"
    if re.search(r"(偶尔|很少|少数时候)", text):
        return "rare"
    if re.search(r"(有时|有时候|有一些时候)", text):
        return "sometimes"
    if re.search(r"(经常|常常|多数时候)", text):
        return "often"
    if re.search(r"(每天|每日|几乎每天|天天)", text):
        return "almost_every_day"
    return frequency_value


def _invoke_structured(prompt: str, parser):
    # 优先走标准结构化解析；如果模型返回了带代码块或注释的 JSON，再做一次容错清洗。
    response = get_base_model().invoke(prompt)
    text = _extract_content(response)
    try:
        return parser.parse(text)
    except Exception:
        cleaned = _clean_json_text(text)
        payload = _normalize_payload(json.loads(cleaned))
        return parser.pydantic_object.model_validate(payload)


def _normalize_turn_analysis(turn: TurnAnalysis) -> TurnAnalysis:
    # 在 reviewer 返回之后做最后一层保守归一化，避免文本描述与枚举字段互相矛盾。
    language = _detect_language(f"{turn.answer}\n{turn.question_text}")
    turn.evidence = [item.strip() for item in turn.evidence if item and item.strip()]
    turn.explanation = turn.explanation.strip()
    turn.review_notes = turn.review_notes.strip()
    original_duration = turn.duration
    original_frequency = turn.frequency
    turn.duration = _normalize_duration_from_text(turn.duration_text, turn.duration)
    turn.frequency = _normalize_frequency_from_text(turn.frequency_text, turn.frequency)

    if turn.duration != original_duration:
        turn.review_notes = f"已根据回答中的持续时间文本“{turn.duration_text}”将 duration 归一化为 {turn.duration}。{turn.review_notes}".strip()
    if turn.frequency != original_frequency:
        turn.review_notes = f"已根据回答中的频率文本“{turn.frequency_text}”将 frequency 归一化为 {turn.frequency}。{turn.review_notes}".strip()

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

    turn.duration_text = _localize_text(turn.duration_text, language)
    turn.frequency_text = _localize_text(turn.frequency_text, language)
    turn.evidence = _localize_text_list(turn.evidence, language)
    turn.explanation = _localize_text(turn.explanation, language)
    turn.review_notes = _localize_text(turn.review_notes, language)
    turn.review_issues = _localize_text_list(turn.review_issues, language)
    turn.retry_count = max(0, turn.retry_count)
    turn.confidence = max(0.0, min(1.0, turn.confidence))
    return turn


def _normalize_session_analysis(session: SessionAnalysis) -> SessionAnalysis:
    language = _detect_language(
        "\n".join([turn.answer for turn in session.turns] + [session.summary, session.explanation])
    )
    session.summary = _localize_text(session.summary, language)
    session.explanation = _localize_text(session.explanation, language)
    session.symptom_summary = _localize_text_list(session.symptom_summary, language)
    session.key_findings = _localize_text_list(session.key_findings, language)
    session.missing_information = _localize_text_list(session.missing_information, language)
    if not session.session_classification:
        session.session_classification = ["healthy"]
    return session


def _review_decision(question_id: int, question_text: str, answer: str, candidate: TurnAnalysis, language: str) -> ReviewDecision:
    # 把“是否通过复核”的判断独立成单独一步，避免 reviewer 一边改结果一边给自己放行。
    parser = get_review_decision_parser()
    prompt = (
        f"{REVIEW_DECISION_SYSTEM_PROMPT}\n\n"
        f"{_language_instruction(language)}\n\n"
        f"{parser.get_format_instructions()}\n\n"
        f"question_id: {question_id}\n"
        f"question_text: {question_text}\n"
        f"answer: {answer}\n"
        f"candidate_result: {json.dumps(candidate.model_dump(mode='json'), ensure_ascii=False)}\n"
    )
    return _invoke_structured(prompt, parser)


def analyze_turn(question_id: int, answer: str) -> TurnAnalysis:
    question = QUESTION_INDEX[question_id]
    language = _detect_language(answer or question.question_text)
    turn_parser = get_turn_parser()
    retry_guidance = ""
    last_reviewed = None
    collected_issues = []

    # 单题分析采用三代理闭环：
    # extractor 先抽取，reviewer 再复核，review_decision 最后裁决是否通过。
    # 如果不通过，就把 guidance 回灌给 extractor 重新抽取，最多重试 3 轮。
    for attempt in range(3):
        extractor_prompt = (
            f"{EXTRACTOR_SYSTEM_PROMPT}\n\n"
            f"{_language_instruction(language)}\n\n"
            f"{turn_parser.get_format_instructions()}\n\n"
            f"question_id: {question.question_id}\n"
            f"question_text: {question.question_text}\n"
            f"answer: {answer}\n"
            f"retry_guidance: {retry_guidance or '首次抽取，无额外修正要求'}\n"
        )
        try:
            draft = _invoke_structured(extractor_prompt, turn_parser)
        except Exception:
            raise

        reviewer_prompt = (
            f"{REVIEWER_SYSTEM_PROMPT}\n\n"
            f"{_language_instruction(language)}\n\n"
            f"{turn_parser.get_format_instructions()}\n\n"
            f"question_id: {question.question_id}\n"
            f"question_text: {question.question_text}\n"
            f"answer: {answer}\n"
            f"extractor_result: {json.dumps(draft.model_dump(mode='json'), ensure_ascii=False)}\n"
        )
        try:
            reviewed = _invoke_structured(reviewer_prompt, turn_parser)
        except Exception:
            raise
        reviewed.question_id = question.question_id
        reviewed.question_text = question.question_text
        reviewed.answer = answer
        reviewed = _normalize_turn_analysis(reviewed)
        last_reviewed = reviewed

        try:
            decision = _review_decision(
                question_id=question.question_id,
                question_text=question.question_text,
                answer=answer,
                candidate=reviewed,
                language=language,
            )
        except Exception:
            raise
        if decision.passed:
            reviewed.review_passed = True
            reviewed.retry_count = attempt
            reviewed.review_issues = collected_issues + decision.issues
            if attempt > 0:
                note = reviewed.review_notes.strip()
                reviewed.review_notes = f"{note} 已通过第{attempt + 1}轮复核。".strip()
            return _normalize_turn_analysis(reviewed)
        collected_issues.extend(_localize_text_list(decision.issues, language))
        retry_guidance = decision.guidance_for_retry or "请严格依据原回答修正无依据字段，并降低过度推断。"

    assert last_reviewed is not None
    last_reviewed.review_passed = False
    last_reviewed.retry_count = 2
    last_reviewed.review_issues = collected_issues
    last_reviewed.review_notes = f"{last_reviewed.review_notes} 经过多轮复核后仍存在疑点，已返回最后一版保守结果。".strip()
    return _normalize_turn_analysis(last_reviewed)


def _build_turns_from_responses(responses: list[dict]) -> list[TurnAnalysis]:
    return [analyze_turn(item["question_id"], item["answer"]) for item in responses]


def _coerce_turns(turns: list[dict] | list[TurnAnalysis]) -> list[TurnAnalysis]:
    return [_normalize_turn_analysis(TurnAnalysis.model_validate(turn)) for turn in turns]


def summarize_session_from_turns(session_id: str, turns: list[dict] | list[TurnAnalysis]) -> SessionAnalysis:
    # 整场总结只消费已经完成复核的结构化 turns，不回到原始问答重新逐题抽取。
    normalized_turns = _coerce_turns(turns)
    language = _detect_language(" ".join(turn.answer for turn in normalized_turns if turn.answer))
    session_parser = get_session_parser()
    summarizer_prompt = (
        f"{SUMMARIZER_SYSTEM_PROMPT}\n\n"
        f"{_language_instruction(language)}\n\n"
        f"{session_parser.get_format_instructions()}\n\n"
        f"session_id: {session_id}\n"
        f"turns: {json.dumps([turn.model_dump(mode='json') for turn in normalized_turns], ensure_ascii=False)}\n"
    )
    summary = _invoke_structured(summarizer_prompt, session_parser)
    return _normalize_session_analysis(SessionAnalysis(
        session_id=session_id,
        turns=normalized_turns,
        overall_risk=summary.overall_risk,
        session_classification=summary.session_classification,
        overall_confidence=summary.overall_confidence,
        summary=summary.summary,
        symptom_summary=summary.symptom_summary,
        key_findings=summary.key_findings,
        missing_information=summary.missing_information,
        explanation=summary.explanation,
    ))


def analyze_session(
    session_id: str,
    responses: list[dict] | None = None,
    turns: list[dict] | list[TurnAnalysis] | None = None,
) -> SessionAnalysis:
    # 优先复用前面逐题分析得到的结构化 turns；仅在兼容路径下才从 responses 补跑单题分析。
    if turns:
        return summarize_session_from_turns(session_id, turns)
    if responses:
        return summarize_session_from_turns(session_id, _build_turns_from_responses(responses))
    raise ValueError("turns or responses cannot both be empty")
