from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from accounts.models import University, UserProfile

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


class UniversityInfoQueryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.university = University.objects.create(
            name="BMSCE",
            country="India",
            allow_public_university_info=True,
            is_active=True,
        )

    @patch("ai_engine.views.answer_question_rag")
    def test_public_university_info_endpoint_returns_answer(self, mock_answer):
        mock_answer.return_value = {
            "answer": "Admissions are open till September.",
            "sources": ["Admissions Policy"],
            "found_in_docs": True,
        }

        res = self.client.post(
            "/api/ai/ask/university-info/public/",
            {
                "university_id": self.university.id,
                "question": "What is the admission deadline?",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data.get("knowledge_base"), "university_info")
        self.assertEqual(res.data.get("visibility_scope"), "public")

    @patch("ai_engine.views.answer_question_rag")
    def test_private_university_info_requires_auth(self, _mock_answer):
        res = self.client.post(
            "/api/ai/ask/university-info/private/",
            {"question": "What are hostel policies?"},
            format="json",
        )
        self.assertEqual(res.status_code, 403)

    @patch("ai_engine.views.answer_question_rag")
    def test_private_university_info_for_authenticated_user(self, mock_answer):
        user = User.objects.create_user(username="student_ai", password="TempPass123!")
        UserProfile.objects.create(
            user=user,
            role="student",
            student_id="AI9001",
            university=self.university,
        )
        self.client.force_authenticate(user=user)

        mock_answer.return_value = {
            "answer": "Hostel guidelines are available in policy docs.",
            "sources": ["Hostel Handbook"],
            "found_in_docs": True,
        }

        res = self.client.post(
            "/api/ai/ask/university-info/private/",
            {"question": "What are hostel policies?"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data.get("knowledge_base"), "university_info")
