
"""
Tests for the QuickNotes document preparation service.
"""

import unittest
import tempfile

from pathlib import Path

from modules.quick_notes import prepare_study_document


class TestQuickNotes(unittest.TestCase):

    def setUp(self):

        # Create a temporary directory.
        self.temp_dir = tempfile.TemporaryDirectory()

        self.folder = Path(self.temp_dir.name)

        # Create a sample study document.
        self.sample_file = self.folder / "machine_learning.txt"

        self.sample_file.write_text(
            """
            Machine Learning is a branch of Artificial Intelligence.

            Supervised learning uses labelled training data.

            Unsupervised learning identifies patterns in unlabelled data.

            Reinforcement learning uses rewards and penalties.
            """,
            encoding="utf-8"
        )

    def tearDown(self):

        # Remove temporary test files.
        self.temp_dir.cleanup()

    def test_prepare_document(self):

        result = prepare_study_document(self.sample_file)

        self.assertTrue(result["success"])

        self.assertEqual(
            result["filename"],
            "machine_learning.txt"
        )

        self.assertIn(
            "Machine Learning",
            result["text"]
        )

    def test_document_provenance(self):

        result = prepare_study_document(self.sample_file)

        provenance = result["provenance"]

        self.assertEqual(
            provenance["filename"],
            "machine_learning.txt"
        )

        self.assertEqual(
            len(provenance["sha256"]),
            64
        )

    def test_document_chunking(self):

        result = prepare_study_document(self.sample_file)

        self.assertGreater(
            result["chunk_count"],
            0
        )

        self.assertTrue(
            isinstance(result["chunks"], list)
        )


if __name__ == "__main__":
    unittest.main()
