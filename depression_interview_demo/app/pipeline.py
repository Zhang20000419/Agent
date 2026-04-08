import json
import os
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


def _extract_evidence(answer: str) -> list[str]:
    parts = [item.strip() for item in re.split(r"[，。；;、\n]", answer) if item.strip()]
    if not parts:
        return []
    return parts[:3]


def _guess_duration(answer: str) -> tuple[str, str]:
    patterns = [
        (r"(一天|1天|两天|2天|几天|数天)", "less_than_2_weeks"),
        (r"(一周|1周|两周|2周|十天|10天|十二天|12天)", "less_than_2_weeks"),
        (r"(三周|3周|四周|4周|一个月内|近一个月)", "2_to_4_weeks"),
        (r"(一个月|1个月|两个月|2个月|三个月内|3个月内)", "1_to_3_months"),
        (r"(三个月以上|3个月以上|半年|几个月|数月|长期)", "more_than_3_months"),
    ]
    for pattern, label in patterns:
        match = re.search(pattern, answer)
        if match:
            return label, match.group(0)
    return "unclear", "不明确"


def _guess_frequency(answer: str) -> tuple[str, str]:
    patterns = [
        (r"(没有|无|从不)", "none"),
        (r"(偶尔|很少|少数时候)", "rare"),
        (r"(有时|有时候|有一些时候)", "sometimes"),
        (r"(经常|常常|多数时候)", "often"),
        (r"(每天|每日|几乎每天|天天)", "almost_every_day"),
    ]
    for pattern, label in patterns:
        match = re.search(pattern, answer)
        if match:
            return label, match.group(0)
    return "unclear", "不明确"


def _guess_polarity(answer: str) -> str:
    deny_patterns = r"(没有|没什么|并不|不会|不太会|从不|无明显|不是)"
    support_patterns = r"(情绪低落|沮丧|绝望|没兴趣|失眠|早醒|疲劳|失败|注意力|烦躁|活着没意思|伤害自己|不如死了|压抑|提不起精神)"
    if re.search(deny_patterns, answer):
        if re.search(support_patterns, answer):
            return "uncertain"
        return "deny"
    if re.search(support_patterns, answer):
        return "support"
    return "uncertain"


def _guess_severity(answer: str, polarity: str, frequency: str, question_id: int) -> str:
    if polarity == "deny":
        return "none"
    if re.search(r"(严重|非常严重|特别严重|无法工作|无法学习|完全做不了)", answer):
        return "severe"
    if question_id == 14:
        if "严重" in answer:
            return "severe"
        if "中等" in answer:
            return "moderate"
        if "轻微" in answer:
            return "mild"
    if frequency == "almost_every_day":
        return "moderate"
    if frequency in {"often", "sometimes"}:
        return "mild"
    if polarity == "support":
        return "mild"
    return "none"


def _symptom_for_question(question_id: int) -> str:
    symptom_map = {
        1: "情绪低落",
        2: "兴趣减退",
        3: "睡眠问题",
        4: "食欲或体重变化",
        5: "疲劳乏力",
        6: "自责或无价值感",
        7: "注意力困难",
        8: "精神运动改变或烦躁",
        9: "自伤或轻生想法",
        10: "功能受损",
        11: "起病时间",
        12: "出现频率",
        13: "持续时长",
        14: "主观严重程度",
        15: "支持因素",
        16: "求助意愿",
    }
    return symptom_map.get(question_id, "访谈症状线索")


def _fallback_turn_analysis(question_id: int, answer: str) -> TurnAnalysis:
    question = QUESTION_INDEX[question_id]
    duration, duration_text = _guess_duration(answer)
    frequency, frequency_text = _guess_frequency(answer)
    polarity = _guess_polarity(answer)
    severity = _guess_severity(answer, polarity, frequency, question_id)
    evidence = _extract_evidence(answer)
    symptom = _symptom_for_question(question_id)

    if question_id == 9 and polarity == "support":
        risk_flag = True
        severity = "severe" if severity in {"mild", "moderate"} else severity
    else:
        risk_flag = polarity == "support" and severity in {"moderate", "severe"}

    confidence = 0.78 if evidence else 0.45
    if polarity == "uncertain":
        confidence = min(confidence, 0.5)
    if polarity == "deny":
        confidence = max(confidence, 0.7)

    explanation = (
        f"该结果依据受试者回答中的证据进行保守判断。"
        f"症状线索为“{symptom}”，极性判断为“{polarity}”，"
        f"持续时间参考“{duration_text}”，频率参考“{frequency_text}”。"
    )
    review_notes = "当前结果由本地保守规则生成，用于保证接口稳定返回；未引入回答之外的信息。"

    turn = TurnAnalysis(
        question_id=question.question_id,
        question_text=question.question_text,
        answer=answer,
        symptom=symptom,
        duration=duration,
        duration_text=duration_text,
        frequency=frequency,
        frequency_text=frequency_text,
        severity=severity,
        polarity=polarity,
        confidence=confidence,
        evidence=evidence,
        explanation=explanation,
        review_notes=review_notes,
        risk_flag=risk_flag,
        review_passed=True,
        retry_count=0,
        review_issues=[],
    )
    return _normalize_turn_analysis(turn)


def _fallback_session_analysis(session_id: str, turns: list[TurnAnalysis]) -> SessionAnalysis:
    support_turns = [turn for turn in turns if turn.polarity == "support"]
    high_risk_turns = [turn for turn in turns if turn.risk_flag]
    severe_count = sum(1 for turn in turns if turn.severity == "severe")
    moderate_count = sum(1 for turn in turns if turn.severity == "moderate")

    if any(turn.question_id == 9 and turn.risk_flag for turn in turns):
        depression_classification = "severe_depression"
        overall_risk = "high"
    elif severe_count >= 2 or moderate_count >= 5:
        depression_classification = "moderately_severe_depression"
        overall_risk = "high"
    elif moderate_count >= 3:
        depression_classification = "moderate_depression"
        overall_risk = "medium"
    elif len(support_turns) >= 2:
        depression_classification = "mild_depression"
        overall_risk = "medium"
    elif support_turns:
        depression_classification = "uncertain"
        overall_risk = "low"
    else:
        depression_classification = "normal"
        overall_risk = "low"

    symptom_summary = [turn.symptom for turn in support_turns[:6]]
    key_findings = [f"第{turn.question_id}题提示{turn.symptom}。" for turn in support_turns[:5]]
    missing_information = []
    if any(turn.duration == "unclear" for turn in turns):
        missing_information.append("部分回答未能明确持续时间。")
    if any(turn.frequency == "unclear" for turn in turns):
        missing_information.append("部分回答未能明确出现频率。")
    if not missing_information:
        missing_information.append("当前 16 题信息基本完整，但仍不能替代正式临床评估。")

    explanation = (
        f"整场结果基于 {len(turns)} 轮回答的保守规则汇总。"
        f"支持性症状线索共 {len(support_turns)} 题，高风险线索共 {len(high_risk_turns)} 题。"
        "该结果用于演示和分层参考，不构成临床诊断。"
    )

    return SessionAnalysis(
        session_id=session_id,
        turns=turns,
        overall_risk=overall_risk,
        depression_classification=depression_classification,
        overall_confidence=0.72 if support_turns else 0.6,
        summary=f"本次访谈的保守汇总结果为 {depression_classification}，风险等级为 {overall_risk}。",
        symptom_summary=symptom_summary or ["当前未形成稳定的阳性症状总结。"],
        key_findings=key_findings or ["当前未发现稳定的高支持度症状证据。"],
        missing_information=missing_information,
        explanation=explanation,
    )


def _normalize_turn_analysis(turn: TurnAnalysis) -> TurnAnalysis:
    # 在 reviewer 返回之后做最后一层保守归一化，避免文本描述与枚举字段互相矛盾。
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

    turn.retry_count = max(0, turn.retry_count)
    turn.confidence = max(0.0, min(1.0, turn.confidence))
    return turn


def _review_decision(question_id: int, question_text: str, answer: str, candidate: TurnAnalysis, language: str) -> ReviewDecision:
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


def _build_session_qa_pairs(responses: list[dict]) -> list[dict]:
    pairs = []
    for item in responses:
        question = QUESTION_INDEX[item["question_id"]]
        pairs.append(
            {
                "question_id": question.question_id,
                "question_text": question.question_text,
                "answer": item["answer"],
            }
        )
    return pairs


def analyze_turn(question_id: int, answer: str) -> TurnAnalysis:
    if os.getenv("USE_MODEL_TURN_ANALYSIS", "true").strip().lower() != "true":
        return _fallback_turn_analysis(question_id, answer)

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
            if os.getenv("ENABLE_LOCAL_FALLBACK", "false").strip().lower() != "true":
                raise
            return _fallback_turn_analysis(question_id, answer)

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
            if os.getenv("ENABLE_LOCAL_FALLBACK", "false").strip().lower() != "true":
                raise
            return _fallback_turn_analysis(question_id, answer)
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
            if os.getenv("ENABLE_LOCAL_FALLBACK", "false").strip().lower() != "true":
                raise
            return _fallback_turn_analysis(question_id, answer)
        if decision.passed:
            reviewed.review_passed = True
            reviewed.retry_count = attempt
            reviewed.review_issues = collected_issues + decision.issues
            if attempt > 0:
                note = reviewed.review_notes.strip()
                reviewed.review_notes = f"{note} 已通过第{attempt + 1}轮复核。".strip()
            return reviewed
        collected_issues.extend(decision.issues)
        retry_guidance = decision.guidance_for_retry or "请严格依据原回答修正无依据字段，并降低过度推断。"

    assert last_reviewed is not None
    last_reviewed.review_passed = False
    last_reviewed.retry_count = 2
    last_reviewed.review_issues = collected_issues
    last_reviewed.review_notes = f"{last_reviewed.review_notes} 经过多轮复核后仍存在疑点，已返回最后一版保守结果。".strip()
    return _normalize_turn_analysis(last_reviewed)


def analyze_session(session_id: str, responses: list[dict]) -> SessionAnalysis:
    # 整场总结的输入不是原始问答，而是 16 轮单题分析后的结构化 turns。
    # 也就是“先逐题 agent 分析，再把全部分析结果一次性交给总结代理”。
    turns = [analyze_turn(item["question_id"], item["answer"]) for item in responses]
    if os.getenv("USE_MODEL_SESSION_SUMMARY", "true").strip().lower() != "true":
        return _fallback_session_analysis(session_id, turns)

    language = _detect_language(" ".join(item["answer"] for item in responses if item.get("answer")))
    session_parser = get_session_parser()
    summarizer_prompt = (
        f"{SUMMARIZER_SYSTEM_PROMPT}\n\n"
        f"{_language_instruction(language)}\n\n"
        f"{session_parser.get_format_instructions()}\n\n"
        f"session_id: {session_id}\n"
        f"turns: {json.dumps([turn.model_dump(mode='json') for turn in turns], ensure_ascii=False)}\n"
    )
    try:
        summary = _invoke_structured(summarizer_prompt, session_parser)
        return SessionAnalysis(
            session_id=session_id,
            turns=turns,
            overall_risk=summary.overall_risk,
            depression_classification=summary.depression_classification,
            overall_confidence=summary.overall_confidence,
            summary=summary.summary,
            symptom_summary=summary.symptom_summary,
            key_findings=summary.key_findings,
            missing_information=summary.missing_information,
            explanation=summary.explanation,
        )
    except Exception:
        if os.getenv("ENABLE_LOCAL_FALLBACK", "false").strip().lower() != "true":
            raise
        return _fallback_session_analysis(session_id, turns)
