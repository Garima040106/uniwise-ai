from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from accounts.models import University, UserProfile
from .models import Document

from .utils import chunk_text


class ChunkTextTests(SimpleTestCase):
    def test_chunk_text_keeps_coverage_and_overlap(self):
        text = (
            "Section one explains the foundational idea in detail. "
            "It introduces definitions and assumptions.\n\n"
            "Section two provides examples, edge cases, and practical notes. "
            "It expands the concept with more context.\n\n"
            "Section three concludes with summary points and revision cues."
        )

        chunks = chunk_text(text, chunk_size=120, overlap=30)

        self.assertGreaterEqual(len(chunks), 2)
        merged = " ".join(chunks)
        self.assertIn("foundational idea", merged)
        self.assertIn("practical notes", merged)
        self.assertIn("revision cues", merged)
        self.assertTrue(all(chunk.strip() for chunk in chunks))


class DocumentIsolationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.uni_a = University.objects.create(name="DSU", country="India")
        self.uni_b = University.objects.create(name="RVCE", country="India")

        self.user_a = User.objects.create_user(username="user_a", password="TempPass123!")
        UserProfile.objects.create(
            user=self.user_a,
            role="student",
            student_id="DSU1001",
            university=self.uni_a,
        )

        self.user_b = User.objects.create_user(username="user_b", password="TempPass123!")
        UserProfile.objects.create(
            user=self.user_b,
            role="student",
            student_id="RV1001",
            university=self.uni_b,
        )

        self.doc_a = Document.objects.create(
            uploaded_by=self.user_a,
            title="DSU Policy",
            file=SimpleUploadedFile("policy.txt", b"policy text"),
            file_type="txt",
            status="completed",
            is_processed=True,
            extracted_text="policy text",
            knowledge_base="university_info",
            visibility="public",
        )

    def test_document_detail_is_university_scoped(self):
        self.client.force_authenticate(user=self.user_b)
        res = self.client.get(f"/api/documents/{self.doc_a.id}/")
        self.assertEqual(res.status_code, 404)
