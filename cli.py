import json

from app.interview_questions import INTERVIEW_QUESTIONS
from app.pipeline import analyze_turn


def main() -> None:
    # CLI 入口主要用于快速验证单题分析，不依赖前端页面。
    print("Mental interview demo. Type answers for the fixed questions. Type 'exit' to quit.")

    for question in INTERVIEW_QUESTIONS:
        print(f"\nQ{question.question_id}: {question.question_text}")
        answer = input("Answer: ").strip()
        if answer.lower() == "exit":
            print("Bye.")
            break

        # 直接复用后端同一套分析流程，避免 CLI 和 API 行为分叉。
        result = analyze_turn(question.question_id, answer)
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
