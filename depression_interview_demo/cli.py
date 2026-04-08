import json

from app.interview_questions import INTERVIEW_QUESTIONS
from app.pipeline import analyze_turn


def main() -> None:
    print("Depression interview demo. Type answers for the fixed questions. Type 'exit' to quit.")

    for question in INTERVIEW_QUESTIONS:
        print(f"\nQ{question.question_id}: {question.question_text}")
        answer = input("Answer: ").strip()
        if answer.lower() == "exit":
            print("Bye.")
            break
        result = analyze_turn(question.question_id, answer)
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
