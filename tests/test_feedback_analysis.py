"""
Tests for BrainCheck student feedback analysis (nlp/feedback_analysis.py).
No database needed: the module only analyses text and rows.

Run:  python -m unittest tests.test_feedback_analysis
"""

import unittest

from nlp.feedback_analysis import (
    analyze_feedback,
    find_aspects,
    rating_to_label,
    split_feedback_sentences,
    summarize_feedback,
)


class TestSingleFeedback(unittest.TestCase):

    def test_positive_feedback_with_aspects(self):
        result = analyze_feedback(
            "Great quiz! The questions were clear and the explanations really helped me.", 5)
        self.assertEqual(result["sentiment"], "Positive")
        self.assertEqual({a["aspect"] for a in result["aspects"]}, {"Questions", "Explanations"})
        self.assertTrue(result["agrees_with_rating"])

    def test_negative_feedback(self):
        result = analyze_feedback("Too difficult and confusing, I hated it.", 1)
        self.assertEqual(result["sentiment"], "Negative")
        self.assertEqual(result["rating_label"], "Negative")

    def test_rating_is_optional(self):
        result = analyze_feedback("The timer was fine.")
        self.assertIsNone(result["rating"])
        self.assertIsNone(result["agrees_with_rating"])

    def test_bad_input_is_rejected(self):
        for text, rating in [("", 3), ("ok", None), ("fine quiz", 0), ("fine quiz", 6),
                             ("fine quiz", "five"), ("fine quiz", True), ("x" * 1001, 3)]:
            with self.assertRaises(ValueError, msg=(text[:10], rating)):
                analyze_feedback(text, rating)


class TestHelpers(unittest.TestCase):

    def test_rating_to_label(self):
        self.assertEqual([rating_to_label(r) for r in (1, 2, 3, 4, 5)],
                         ["Negative", "Negative", "Neutral", "Positive", "Positive"])

    def test_but_splits_contrasting_parts(self):
        self.assertEqual(split_feedback_sentences("Questions were clear but the timer was too short."),
                         ["Questions were clear", "the timer was too short"])

    def test_aspect_keywords_match_word_starts(self):
        self.assertEqual(find_aspects("It was explained well"), ["Explanations"])
        self.assertEqual(find_aspects("Nothing relevant here at all"), ["Questions"])  # "relevant"
        self.assertEqual(find_aspects("Lovely day"), [])


class TestSummary(unittest.TestCase):

    def rows(self):
        data = [
            ("Great quiz, the questions were clear!", 5, 90),
            ("Too difficult and the timer was too fast, I hated it.", 1, 30),
            ("Nice coverage of the topic, easy to follow.", 4, 80),
        ]
        return [{**analyze_feedback(text, rating), "score_percentage": score}
                for text, rating, score in data]

    def test_distribution_and_scores(self):
        summary = summarize_feedback(self.rows())
        self.assertEqual(summary["total_feedback"], 3)
        self.assertEqual(summary["distribution"], {"Positive": 2, "Neutral": 0, "Negative": 1})
        self.assertEqual(summary["average_score_by_sentiment"]["Positive"], 85.0)
        self.assertEqual(summary["average_score_by_sentiment"]["Negative"], 30.0)
        self.assertIsNone(summary["average_score_by_sentiment"]["Neutral"])
        self.assertGreater(summary["score_sentiment_correlation"], 0.5)

    def test_evaluation_against_star_ratings(self):
        evaluation = summarize_feedback(self.rows())["evaluation"]
        self.assertEqual(evaluation["samples"], 3)
        self.assertEqual(evaluation["accuracy"], 1.0)

    def test_empty_summary(self):
        summary = summarize_feedback([])
        self.assertEqual(summary["total_feedback"], 0)
        self.assertIsNone(summary["evaluation"])
        self.assertIsNone(summary["score_sentiment_correlation"])


if __name__ == "__main__":
    unittest.main()
