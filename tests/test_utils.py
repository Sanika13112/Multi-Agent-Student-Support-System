
import unittest
import tempfile

from pathlib import Path

from modules.common.utils import (
    clean_text,
    validate_text,
    format_file_size,
    chunk_text,
    calculate_file_hash
)


class TestCommonUtils(unittest.TestCase):

    def test_clean_text(self):

        result = clean_text("Hello    Student\n\nSupport")

        self.assertEqual(result, "Hello Student Support")

    def test_validate_text(self):

        self.assertTrue(validate_text("Hello"))

        self.assertFalse(validate_text("   "))

    def test_format_file_size(self):

        result = format_file_size(1024)

        self.assertEqual(result, "1.00 KB")

    def test_chunk_text(self):

        text = "A" * 2500

        chunks = chunk_text(
            text,
            chunk_size=1000,
            overlap=150
        )

        self.assertEqual(len(chunks), 3)

        self.assertEqual(len(chunks[0]), 1000)

        self.assertEqual(len(chunks[1]), 1000)

    def test_file_hash(self):

        with tempfile.TemporaryDirectory() as folder:

            file_path = Path(folder) / "sample.txt"

            file_path.write_text(
                "Student Support System",
                encoding="utf-8"
            )

            hash_value = calculate_file_hash(file_path)

            self.assertEqual(len(hash_value), 64)


if __name__ == "__main__":
    unittest.main()
