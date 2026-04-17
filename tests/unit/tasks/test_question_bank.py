import tempfile
import unittest
from pathlib import Path

from depression_detection.tasks.qa.question_bank import get_question_index, load_interview_questions


class QuestionBankTests(unittest.TestCase):
    def test_load_interview_questions_from_static_directory(self):
        questions = load_interview_questions()
        self.assertEqual(len(questions), 16)
        self.assertEqual(questions[0].question_id, 1)
        self.assertEqual(questions[-1].question_id, 16)

    def test_question_loader_uses_files_as_single_source_of_truth(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            (base / "1.txt").write_text("问题一", encoding="utf-8")
            (base / "2.txt").write_text("问题二", encoding="utf-8")
            questions = load_interview_questions(str(base))
            index = get_question_index(str(base))

        self.assertEqual([item.question_text for item in questions], ["问题一", "问题二"])
        self.assertEqual(sorted(index), [1, 2])
        self.assertEqual(index[2].question_text, "问题二")


if __name__ == "__main__":
    unittest.main()
