
"""
Tests for the NLP text preprocessing module.

Purpose:
Check whether cleaning, tokenization, and stop-word
removal work as expected.
"""

import unittest

# Import the function we want to test.
from nlp.preprocess import preprocess_text


class TestPreprocessing(unittest.TestCase):

    def test_lowercase_and_stopwords(self):
        """Check basic text preprocessing."""

        result = preprocess_text(
            "Can you PLEASE explain Machine Learning?"
        )

        self.assertEqual(
            result,
            ["please", "explain", "machine", "learning"]
        )

    def test_negation_is_preserved(self):
        """Ensure that the word 'not' is not removed."""

        result = preprocess_text(
            "I do not understand NLP!"
        )

        self.assertIn("not", result)

    def test_empty_text(self):
        """An empty question should return an empty list."""

        result = preprocess_text("")

        self.assertEqual(result, [])

    def test_invalid_input(self):
        """Non-text input should raise a TypeError."""

        with self.assertRaises(TypeError):
            preprocess_text(123)


# Run the tests when this file is executed directly.
if __name__ == "__main__":
    unittest.main()
