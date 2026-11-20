"""
Tests for the end-to-end NLP pipeline (nlp/pipeline.py).

The Ollama LLM and the MyMemory cloud translator are replaced with fakes
(unittest.mock), so these tests run offline and need neither service.

Run:  python -m unittest tests.test_pipeline
"""

import json
import unittest
from pathlib import Path
from unittest import mock

from nlp.pipeline import check_llm_output, render_markdown, run_pipeline

SAMPLE_PDF = Path(__file__).resolve().parents[1] / "data" / "DAA_Unit5_Computational_Complexity.pdf"

FAKE_LLM_OUTPUT = (
    "Summary:\nNP problems are verified in polynomial time.\n\n"
    "Key points:\n- P is solvable in polynomial time\n- SAT is NP-complete\n\n"
    "Exam question:\nWhat is an NP-complete problem?"
)

FAKE_TRANSLATION = {
    "service": "MyMemory Translation API (cloud)",
    "source_language": "en",
    "target_language": "mr",
    "target_language_name": "Marathi",
    "source_text": "x",
    "translated_text": "translated",
}


def stage(report, number):
    """Find one stage record by its number."""

    return next(item for item in report["stages"] if item["number"] == number)


class TestPipelineOffline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Run the pipeline once on the sample PDF without LLM or translation."""

        cls.report = run_pipeline(file_path=str(SAMPLE_PDF), use_llm=False, num_topics=4)

    def test_all_offline_stages_finish(self):
        statuses = [item["status"] for item in self.report["stages"]]
        self.assertEqual(statuses, ["done"] * 9 + ["skipped", "skipped"])

    def test_each_co_is_covered(self):
        cos = {item["co"] for item in self.report["stages"]}
        self.assertEqual(cos, {"CO1", "CO2", "CO3", "CO4"})

    def test_co1_numbers(self):
        extraction = stage(self.report, 1)["details"]
        self.assertEqual(extraction["pages"], 15)

        vectors = stage(self.report, 4)["details"]
        self.assertGreater(vectors["vocabulary_size"], 100)
        self.assertEqual(len(vectors["matrix_shape"]), 2)

    def test_lda_uses_requested_topic_count(self):
        self.assertEqual(stage(self.report, 8)["details"]["num_topics"], 4)

    def test_report_is_json_and_has_no_full_text(self):
        """The report goes to the browser as JSON; full texts stay out of it."""

        json.dumps(self.report)                     # raises if anything is not JSON-safe
        self.assertNotIn("text", stage(self.report, 1)["details"])
        self.assertNotIn("cleaned_text", stage(self.report, 2)["details"])

    def test_markdown_report(self):
        markdown = render_markdown(self.report)
        self.assertIn("# NLP Pipeline Report", markdown)
        self.assertIn("| 8 | CO3 | Topic modeling |", markdown)


class TestPipelineWithServices(unittest.TestCase):

    TEXT = (
        "Deadlock is a situation where two transactions wait for each other forever. "
        "The Database Management System (DBMS) detects deadlocks with a wait-for graph. "
        "A cycle in the wait-for graph means a deadlock exists. "
        "Prevention removes one of the four necessary conditions. "
        "Detection runs in O(n) time for n transactions. "
        "Recovery aborts a victim transaction and restarts it later. "
        "Timeouts are a simple but imprecise way to handle deadlocks."
    )

    @mock.patch("nlp.multilingual.translate", return_value=dict(FAKE_TRANSLATION))
    @mock.patch("modules.common.ai_client.generate_response", return_value=FAKE_LLM_OUTPUT)
    def test_llm_and_translation_stages(self, fake_llm, fake_translate):
        report = run_pipeline(text=self.TEXT, use_llm=True, translate_to="mr", num_topics=2)

        llm = stage(report, 10)
        self.assertEqual(llm["status"], "done")
        self.assertTrue(llm["details"]["checks"]["format_followed"])

        # The prompt sent to the model contains what earlier stages found.
        prompt = fake_llm.call_args.args[0]
        self.assertIn("Deadlock:", prompt)          # extracted definition
        self.assertIn("Topics found by LDA", prompt)

        translation = stage(report, 11)
        self.assertEqual(translation["status"], "done")
        self.assertEqual(translation["details"]["translated_from"], "LLM summary")
        fake_translate.assert_called_once_with(FAKE_LLM_OUTPUT, "mr")

    @mock.patch("modules.common.ai_client.generate_response",
                side_effect=RuntimeError("Make sure Ollama is running"))
    def test_llm_failure_is_reported_not_faked(self, fake_llm):
        report = run_pipeline(text=self.TEXT, use_llm=True)
        llm = stage(report, 10)
        self.assertEqual(llm["status"], "failed")
        self.assertIn("Ollama", llm["summary"])
        self.assertEqual(llm["details"], {})
        # Stages that do not need the LLM still finish.
        self.assertEqual(stage(report, 6)["status"], "done")

    def test_empty_input_fails_cleanly(self):
        report = run_pipeline(text="   ", use_llm=False)
        self.assertEqual(stage(report, 1)["status"], "failed")
        self.assertEqual(stage(report, 2)["status"], "skipped")


class TestLlmChecks(unittest.TestCase):

    def test_format_and_grounding(self):
        info = {"key_terms": [{"term": "deadlock"}, {"term": "graph"}, {"term": "banana"}]}
        checks = check_llm_output("Summary: deadlock\nKey points: graph\nExam question: ?", info)
        self.assertTrue(checks["format_followed"])
        self.assertEqual(checks["key_terms_used"], ["deadlock", "graph"])
        self.assertEqual(checks["grounding_percent"], 66.7)

    def test_missing_section_detected(self):
        checks = check_llm_output("Summary: only this", {"key_terms": []})
        self.assertFalse(checks["format_followed"])
        self.assertIsNone(checks["grounding_percent"])


if __name__ == "__main__":
    unittest.main()
