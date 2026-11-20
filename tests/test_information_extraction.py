"""
Tests for the information extraction module (CO2).

Run:  python -m unittest tests.test_information_extraction
"""

import unittest

from nlp.information_extraction import (
    evaluate_on_labelled_set,
    extract_acronyms,
    extract_complexity_expressions,
    extract_definitions,
    extract_information,
    find_long_form,
    split_sentences,
)


class TestSentenceSplitting(unittest.TestCase):

    def test_slide_heading_is_kept_separate(self):
        """A one-word slide heading must not be glued to the next line."""

        sentences = split_sentences("Timetabling\nClass and exam scheduling is graph \ncolouring.")
        self.assertEqual(sentences, ["Timetabling", "Class and exam scheduling is graph colouring"])

    def test_hyphenated_line_break_is_rejoined(self):
        self.assertEqual(split_sentences("Feature selection is NP-\nhard."), ["Feature selection is NP-hard"])

    def test_wrapped_sentence_is_joined(self):
        """A line ending in "the" continues on the next line."""

        sentences = split_sentences("The algorithm finds the\nShortest path quickly.")
        self.assertEqual(sentences, ["The algorithm finds the Shortest path quickly"])


class TestDefinitions(unittest.TestCase):

    def test_is_pattern(self):
        result = extract_definitions("Deadlock is a situation where two transactions wait forever.")
        self.assertEqual(result[0]["term"], "Deadlock")

    def test_called_pattern(self):
        result = extract_definitions(
            "A problem that can be solved in polynomial time is called a tractable problem.")
        self.assertEqual(result[0]["term"], "tractable problem")

    def test_pronoun_subject_is_ignored(self):
        self.assertEqual(extract_definitions("It is important to revise every unit before the exam."), [])

    def test_list_subject_is_ignored(self):
        """"X and Y are ..." is a classification, not a definition of one term."""

        self.assertEqual(extract_definitions("TSP and the Halting problem are NP-Hard but not in NP."), [])


class TestAcronyms(unittest.TestCase):

    def test_schwartz_hearst_matches_inner_letters(self):
        """DBMS takes the B from inside "DataBase"; first-letter matching would fail."""

        self.assertEqual(find_long_form("DBMS", "Database Management System"), "Database Management System")

    def test_extract_from_text(self):
        result = extract_acronyms("The Travelling Salesman Problem (TSP) is hard.")
        self.assertEqual(result, [{"acronym": "TSP", "expansion": "Travelling Salesman Problem"}])

    def test_non_acronym_brackets_are_ignored(self):
        self.assertEqual(extract_acronyms("See the diagram (Fig) below."), [])


class TestOtherExtractors(unittest.TestCase):

    def test_complexity_expressions(self):
        found = extract_complexity_expressions("Merge sort is O(n log n) but brute force is O(n!).")
        self.assertEqual(found, ["O(n log n)", "O(n!)"])

    def test_extract_information_counts(self):
        text = ("Deadlock is a situation where processes wait forever. "
                "The Operating System (OS) detects it. Detection costs O(n) time. "
                "Deadlock prevention removes one of the four conditions.")
        info = extract_information(text)
        self.assertEqual(info["counts"]["definitions"], 1)
        self.assertEqual(info["acronyms"][0]["acronym"], "OS")
        self.assertIn("O(n)", info["complexity_expressions"])

    def test_empty_text_is_rejected(self):
        with self.assertRaises(ValueError):
            extract_information("   ")


class TestEvaluation(unittest.TestCase):

    def test_labelled_set_scores(self):
        """Pins the scores reported in RUBRIC.md; update both together."""

        result = evaluate_on_labelled_set()
        self.assertEqual(result["samples"], 12)
        self.assertAlmostEqual(result["definitions"]["f1_score"], 0.9091, places=3)
        self.assertAlmostEqual(result["acronyms"]["f1_score"], 0.75, places=3)


if __name__ == "__main__":
    unittest.main()
