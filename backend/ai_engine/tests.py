from unittest.mock import patch

from django.test import SimpleTestCase

from .utils import (
    _parse_json_array,
    answer_question_rag,
    generate_quiz,
)


class AIUtilsTests(SimpleTestCase):
    def test_parse_json_array_recovers_trailing_comma(self):
        raw = """
        Here you go:
        [
          {"question": "Q1", "answer": "A1",}
        ]
        """
        parsed = _parse_json_array(raw)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["question"], "Q1")

    @patch("ai_engine.utils._build_study_context", return_value=("Context block", []))
    @patch("ai_engine.utils.query_ollama")
    def test_generate_quiz_retries_to_fill_missing_questions(self, mock_query_ollama, _mock_context):
        mock_query_ollama.side_effect = [
            """
            [
              {
                "question": "What is the first concept?",
                "option_a": "Concept A",
                "option_b": "Concept B",
                "option_c": "Concept C",
                "option_d": "Concept D",
                "correct_answer": "A",
                "explanation": "From section one."
              }
            ]
            """,
            """
            [
              {
                "question": "How is the second concept applied?",
                "option_a": "Usage A",
                "option_b": "Usage B",
                "option_c": "Usage C",
                "option_d": "Usage D",
                "correct_answer": "B",
                "explanation": "From section two."
              }
            ]
            """,
        ]

        questions = generate_quiz(
            text="placeholder",
            university_id=10,
            course_id=5,
            document_id=2,
            num_questions=2,
            difficulty="medium",
        )

        self.assertEqual(len(questions), 2)
        self.assertNotEqual(questions[0]["question"], questions[1]["question"])
        self.assertIn(questions[0]["correct_answer"], {"A", "B", "C", "D"})
        self.assertIn(questions[1]["correct_answer"], {"A", "B", "C", "D"})

    @patch("ai_engine.utils.build_rag_context", return_value=("Context", ["Doc 1"]))
    @patch("ai_engine.utils.query_ollama", return_value="Error: service unavailable")
    def test_answer_question_rag_handles_model_failure(self, _mock_query, _mock_context):
        result = answer_question_rag("What is X?", university_id=1)
        self.assertIn("could not generate an answer", result["answer"].lower())
        self.assertEqual(result["sources"], ["Doc 1"])
        self.assertTrue(result["found_in_docs"])
