
"""
Tests for the common document loader.
"""

import unittest
import tempfile

from pathlib import Path

from modules.common.document_loader import (
    load_document,
    validate_document,
    DocumentError
)


class TestDocumentLoader(unittest.TestCase):

    def setUp(self):
        # Create a temporary folder for test files.
        self.temp_dir = tempfile.TemporaryDirectory()

        self.folder = Path(self.temp_dir.name)

        # Create a sample TXT document.
        self.txt_file = self.folder / "sample.txt"

        self.txt_file.write_text(
            "Machine Learning is a branch of Artificial Intelligence.",
            encoding="utf-8"
        )

    def tearDown(self):
        # Remove temporary test files.
        self.temp_dir.cleanup()

    def test_load_txt_file(self):

        result = load_document(self.txt_file)

        self.assertEqual(result["filename"], "sample.txt")

        self.assertEqual(result["file_type"], "txt")

        self.assertIn("Machine Learning", result["text"])

        self.assertEqual(result["page_count"], 1)

    def test_invalid_file_extension(self):

        wrong_file = self.folder / "sample.docx"
        wrong_file.write_text("Test", encoding="utf-8")

        with self.assertRaises(DocumentError):
            validate_document(wrong_file)

    def test_missing_file(self):

        missing_file = self.folder / "missing.txt"

        with self.assertRaises(DocumentError):
            validate_document(missing_file)

    def test_empty_document(self):

        empty_file = self.folder / "empty.txt"
        empty_file.write_text("", encoding="utf-8")

        with self.assertRaises(DocumentError):
            load_document(empty_file)


if __name__ == "__main__":
    unittest.main()
