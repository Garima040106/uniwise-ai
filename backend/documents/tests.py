from django.test import SimpleTestCase

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
