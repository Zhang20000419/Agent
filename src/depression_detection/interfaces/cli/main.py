import json

from depression_detection.bootstrap.container import get_container


def main() -> None:
    service = get_container().qa_service()
    print("Mental interview demo. Type answers for the fixed questions. Type 'exit' to quit.")
    for question in service.get_questions():
        print(f"\nQ{question.question_id}: {question.question_text}")
        answer = input("Answer: ").strip()
        if answer.lower() == "exit":
            print("Bye.")
            break
        result = service.analyze_turn(question.question_id, answer)
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
