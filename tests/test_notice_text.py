"""
Tests for the Notice Translator: text cleaning, information extraction,
and reading PDF and Word (.docx) notices.
EasyOCR is never run: OCR is replaced with a fake where a test needs it.

Run:  python -m unittest tests.test_notice_text
"""

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from modules.notice_translator import service
from modules.notice_translator.service import extract_information, preprocess_text


class TestPreprocessKeepsValuesIntact(unittest.TestCase):
    """The cleaning step used to add spaces inside times, dates and emails."""

    def test_time(self):
        self.assertEqual(preprocess_text("Time: 10:30 AM"), "Time: 10:30 AM")

    def test_dotted_date(self):
        self.assertEqual(preprocess_text("Date: 18.11.2026"), "Date: 18.11.2026")

    def test_email_and_website(self):
        self.assertEqual(preprocess_text("Mail hod.cse@mitaoe.ac.in or visit www.mitaoe.ac.in"),
                         "Mail hod.cse@mitaoe.ac.in or visit www.mitaoe.ac.in")

    def test_spacing_is_still_fixed(self):
        self.assertEqual(preprocess_text("Date:18/11/2026 , submit report.Late entries rejected"),
                         "Date: 18/11/2026, submit report. Late entries rejected")


class TestNoticeExtraction(unittest.TestCase):

    NOTICE = ("NOTICE\nDate: 18.11.2026\nAll students are informed that the seminar starts at 10:30 AM.\n"
              "Venue: Seminar Hall\nContact hod.cse@mitaoe.ac.in or 9876543210.")

    def test_values_are_found(self):
        info = extract_information(self.NOTICE)
        self.assertEqual(info["dates"], ["18.11.2026"])
        self.assertEqual(info["times"], ["10:30 AM"])
        self.assertEqual(info["emails"], ["hod.cse@mitaoe.ac.in"])
        self.assertEqual(info["phone_numbers"], ["9876543210"])

    def test_at_inside_that_is_not_a_venue(self):
        info = extract_information("All students are informed that the report is due.")
        self.assertEqual(info["venues"], [])

    def test_devanagari_venue_words(self):
        self.assertEqual(len(extract_information("स्थान: कक्ष 304")["venues"]), 1)
        self.assertEqual(len(extract_information("ठिकाण: सभागृह")["venues"]), 1)


# ----------------------------------------------------------------------
# PDF and Word (.docx) notices
# ----------------------------------------------------------------------

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def make_docx(path, body_xml, header_text=None):
    """Write a minimal .docx (a ZIP with word/document.xml) without python-docx."""

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", f"<w:document {W}><w:body>{body_xml}</w:body></w:document>")
        if header_text:
            archive.writestr("word/header1.xml",
                             f"<w:hdr {W}><w:p><w:r><w:t>{header_text}</w:t></w:r></w:p></w:hdr>")


def para(text):
    return f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"


class TestDocumentNotices(unittest.TestCase):

    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())

    def test_docx_paragraphs_table_and_header(self):
        path = self.folder / "notice.docx"
        table = ("<w:tbl><w:tr><w:tc>" + para("Venue") + "</w:tc><w:tc>" + para("Room 304")
                 + "</w:tc></w:tr></w:tbl>")
        make_docx(path, para("NOTICE") + para("Date: 18.11.2026") + table, header_text="MIT Academy of Engineering")

        result = service.extract_notice_text(path)
        self.assertEqual(result["source_type"], "docx")
        self.assertEqual(result["segments"],
                         ["MIT Academy of Engineering", "NOTICE", "Date: 18.11.2026", "Venue | Room 304"])

    def test_broken_and_old_word_files(self):
        broken = self.folder / "broken.docx"
        broken.write_bytes(b"not a zip")
        with self.assertRaisesRegex(ValueError, "could not be read"):
            service.extract_notice_text(broken)

        old = self.folder / "old.doc"
        old.write_bytes(b"old word file")
        with self.assertRaisesRegex(ValueError, "save as .docx"):
            service.extract_notice_text(old)

    def test_empty_docx(self):
        path = self.folder / "empty.docx"
        make_docx(path, "")
        with self.assertRaisesRegex(ValueError, "No text was found"):
            service.extract_notice_text(path)

    def test_text_pdf_is_read_without_ocr(self):
        import pymupdf
        path = self.folder / "notice.pdf"
        with pymupdf.open() as pdf:
            pdf.new_page().insert_text((72, 72), "NOTICE\nSeminar on 18/11/2026 at 10:30 AM in Room 304")
            pdf.save(path)

        with mock.patch.object(service, "get_ocr_reader", side_effect=AssertionError("OCR not needed")):
            result = service.extract_notice_text(path)

        self.assertEqual(result["source_type"], "pdf_text")
        self.assertIn("10:30 AM", result["text"])

    def test_scanned_pdf_page_uses_ocr(self):
        import pymupdf
        path = self.folder / "scan.pdf"
        with pymupdf.open() as pdf:
            pdf.new_page()          # blank page = no text layer, like a scan
            pdf.save(path)

        fake_reader = mock.Mock()
        fake_reader.readtext.return_value = [(None, "NOTICE from scan", 0.9)]
        with mock.patch.object(service, "get_ocr_reader", return_value=fake_reader):
            result = service.extract_notice_text(path)

        self.assertEqual(result["source_type"], "pdf_scanned")
        self.assertEqual(result["segments"], ["NOTICE from scan"])
        page_image = fake_reader.readtext.call_args.args[0]
        self.assertEqual(page_image.ndim, 2)          # prepared grayscale page image

    def test_missing_easyocr_gives_install_message(self):
        image = self.folder / "notice.png"
        image.write_bytes(b"\x89PNG")
        with mock.patch.object(service, "_ocr_reader", None), \
                mock.patch.dict(sys.modules, {"easyocr": None}):
            with self.assertRaisesRegex(service.NoticeDependencyError, "pip install easyocr"):
                service.extract_notice_text(image)



# ----------------------------------------------------------------------
# OCR quality control and translation-memory guard
# ----------------------------------------------------------------------

class TestOcrQuality(unittest.TestCase):

    def test_noise_and_unsure_lines_are_removed(self):
        results = [
            (None, "Rani Durgavati Vishwavidyalaya, Jabalpur", 0.91),
            (None, "दिनांक 18/11/2026", 0.80),           # Hindi with vowel signs: kept
            (None, "14181", 0.85),                       # roll number: kept
            (None, "*-10*+7*20*7", 0.60),                # mostly symbols: removed
            (None, "dPiTa +l# 4k Jitbh Ellaa HLll", 0.12),   # EasyOCR unsure: removed
        ]
        lines, removed = service._ocr_lines(results)
        self.assertEqual([line["text"] for line in lines],
                         ["Rani Durgavati Vishwavidyalaya, Jabalpur", "दिनांक 18/11/2026", "14181"])
        self.assertEqual(removed, 2)

    def test_quality_flag(self):
        good = [{"ocr_confidence": 0.9}, {"ocr_confidence": 0.8}]
        self.assertFalse(service.ocr_quality(good, 0)["low"])
        unsure = [{"ocr_confidence": 0.4}, {"ocr_confidence": 0.5}]
        self.assertTrue(service.ocr_quality(unsure, 0)["low"])
        self.assertTrue(service.ocr_quality(good, 5)["low"])          # most lines were noise
        direct = [{"ocr_confidence": None}]
        self.assertFalse(service.ocr_quality(direct, 0)["ocr_used"])  # PDF/Word text

    def test_image_is_prepared_for_ocr(self):
        from PIL import Image
        folder = Path(tempfile.mkdtemp())
        photo = Image.new("RGB", (400, 200), "white")
        exif = Image.Exif()
        exif[0x0112] = 6                                # "rotate 90°" as phones store it
        photo.save(folder / "photo.jpg", exif=exif)

        array = service.prepare_image_for_ocr(str(folder / "photo.jpg"))
        self.assertEqual(array.ndim, 2)                 # grayscale
        height, width = array.shape
        self.assertGreater(height, width)               # turned upright (portrait)
        self.assertEqual(max(height, width), 400 * 3)   # enlarged, at most 3x


class TestTranslationMemoryGuard(unittest.TestCase):

    def setUp(self):
        from modules.notice_translator.translation import choose_translation
        self.choose = choose_translation

    def response(self, main, matches):
        return {"responseData": {"translatedText": main}, "matches": matches}

    def test_unrelated_memory_match_is_replaced_by_machine_translation(self):
        result = self.response("Chatrapati Shivaji Maharaj Vastu Sangrahalaya", [
            {"segment": "छत्रपति शिवाजी महाराज वास्तु संग्रहालय", "translation":
             "Chatrapati Shivaji Maharaj Vastu Sangrahalaya", "created-by": "someone"},
            {"segment": "गणित विभाग", "translation": "Department of Mathematics", "created-by": "MT!"},
        ])
        self.assertEqual(self.choose("गणित विभाग", result), "Department of Mathematics")

    def test_memory_match_of_same_sentence_is_kept(self):
        result = self.response("Department of Mathematics", [
            {"segment": "गणित विभाग", "translation": "Department of Mathematics", "created-by": "teacher"},
            {"segment": "गणित विभाग", "translation": "Maths department", "created-by": "MT!"},
        ])
        self.assertEqual(self.choose("गणित विभाग", result), "Department of Mathematics")

    def test_without_matches_the_main_answer_is_used(self):
        self.assertEqual(self.choose("नमस्ते", self.response("Hello", [])), "Hello")


if __name__ == "__main__":
    unittest.main()
