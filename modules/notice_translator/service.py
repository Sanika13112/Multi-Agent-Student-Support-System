
"""
Notice Translator Service
-------------------------
Offline OCR + language detection + NLP information extraction
for English, Hindi and Marathi college notices.

Accepted files:
    JPG / PNG  -> EasyOCR reads the text from the image
    PDF        -> text is read directly; scanned pages are OCR'd
    DOCX       -> paragraphs and tables are read from the Word file

EasyOCR, fastText and PyMuPDF are imported only when needed, so a Word
file does not need EasyOCR, and a missing package gives a clear message.
"""

from pathlib import Path
from collections import defaultdict
import io
import re
import unicodedata
import zipfile
import xml.etree.ElementTree as ET


class NoticeDependencyError(RuntimeError):
    """A package needed for this file type is not installed."""


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LANGUAGE_MODEL_PATH = PROJECT_ROOT / "models" / "lid.176.ftz"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
DOCUMENT_EXTENSIONS = {".pdf", ".docx"}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | DOCUMENT_EXTENSIONS

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 10              # notices are short; keeps OCR time reasonable
MIN_PAGE_TEXT_CHARS = 20        # fewer characters than this = scanned page, use OCR
PDF_OCR_DPI = 200               # resolution used to turn a scanned page into an image

WORD_NAMESPACE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# OCR quality control
MIN_OCR_CONFIDENCE = 0.35       # EasyOCR's own score; lower lines are usually noise
MIN_TEXT_CHARACTER_SHARE = 0.6  # lines that are mostly symbols ("*-10*+7*") are dropped
LOW_QUALITY_CONFIDENCE = 0.55   # average below this -> warn that text may be wrong
OCR_TARGET_LONG_SIDE = 2000     # small photos are enlarged to about this many pixels
OCR_MAX_LONG_SIDE = 3000        # very large photos are shrunk (faster, same accuracy)

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
}

MIN_LANGUAGE_CONFIDENCE = 0.50

_ocr_reader = None
_language_model = None


# --------------------------------------------------
# LOAD MODELS
# --------------------------------------------------

def get_ocr_reader():
    """Load EasyOCR once and reuse it."""

    global _ocr_reader

    if _ocr_reader is None:
        try:
            import easyocr
        except ImportError as error:
            raise NoticeDependencyError(
                "EasyOCR is not installed, so images and scanned PDFs cannot be read. "
                "Run: python -m pip install easyocr"
            ) from error

        print("Loading OCR model...")
        # Hindi and Marathi share EasyOCR's Devanagari model;
        # adding "mr" lets it read Marathi-only letters such as ळ.
        _ocr_reader = easyocr.Reader(
            ["en", "hi", "mr"],
            gpu=False
        )

    return _ocr_reader


def get_language_model():
    """Load the local fastText model once."""

    global _language_model

    if _language_model is None:
        if not LANGUAGE_MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Language model not found: {LANGUAGE_MODEL_PATH}"
            )

        try:
            import fasttext
        except ImportError as error:
            raise NoticeDependencyError(
                "fastText is not installed, so the language cannot be detected. "
                "Run: python -m pip install fasttext-wheel"
            ) from error

        print("Loading language detection model...")
        _language_model = fasttext.load_model(
            str(LANGUAGE_MODEL_PATH)
        )

    return _language_model


# --------------------------------------------------
# NLP: TEXT PREPROCESSING
# --------------------------------------------------

def clean_text(text):
    """Normalize whitespace and remove unnecessary blank lines."""

    if not isinstance(text, str):
        return ""

    text = text.replace("\r", "\n")
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    return text.strip()


def preprocess_text(text):
    """
    Prepare OCR text for NLP processing.
    Preserves dates, numbers and punctuation.
    """

    text = clean_text(text)

    # Normalize common OCR spacing problems, without breaking times
    # (10:30), dotted dates (18.11.2026), emails, websites or amounts (Rs.500).

    # 1. No space before punctuation: "word ," -> "word,".
    text = re.sub(r" +([,;:.!?])", r"\1", text)

    # 2. One space after , ; : ...
    text = re.sub(r"([,;:]) *", r"\1 ", text)

    # ... but keep numbers together: "10: 30" -> "10:30", "1, 000" -> "1,000".
    text = re.sub(r"(\d): (\d)", r"\1:\2", text)
    text = re.sub(r"(\d), (\d{3})\b", r"\1,\2", text)

    # 3. Space after a sentence end only between a lowercase word and a
    #    capitalised one: "report.Late" -> "report. Late".
    text = re.sub(r"(?<=[a-z])([.!?])(?=[A-Z])", r"\1 ", text)

    return clean_text(text)


def split_sentences(text):
    """Split text into individual sentences."""

    text = preprocess_text(text)

    if not text:
        return []

    # Basic multilingual sentence boundaries.
    sentences = re.split(
        r"(?<=[.!?।॥])\s+|\n+",
        text
    )

    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]


# --------------------------------------------------
# NLP: INFORMATION EXTRACTION
# --------------------------------------------------

def extract_information(text):
    """
    Extract useful information from a college notice.

    Uses lightweight pattern matching, so no additional
    machine-learning model is required.
    """

    text = preprocess_text(text)

    # Email addresses
    emails = list(set(
        re.findall(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            text
        )
    ))

    # Phone numbers: Indian mobile and common contact formats.
    phone_numbers = list(set(
        re.findall(
            r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)",
            text
        )
    ))

    # Dates: DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
    numeric_dates = list(set(
        re.findall(
            r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"
            r"|\b\d{1,2}\.\d{1,2}\.\d{2,4}\b",
            text
        )
    ))

    # Times: 10:30 AM, 14:30, etc.
    times = list(set(
        re.findall(
            r"\b(?:0?[1-9]|1[0-2]):[0-5]\d\s?(?:AM|PM)\b"
            r"|\b(?:[01]?\d|2[0-3]):[0-5]\d\b",
            text,
            flags=re.IGNORECASE
        )
    ))

    # Common deadline-related words in English, Hindi and Marathi.
    deadline_keywords = [
        "deadline", "last date", "submit by", "due date",
        "अंतिम तारीख", "अंतिम दिनांक", "जमा करने की अंतिम तारीख",
        "शेवटची तारीख", "अंतिम मुदत", "सादर करण्याची अंतिम तारीख"
    ]

    deadline_sentences = [
        sentence
        for sentence in split_sentences(text)
        if any(
            keyword in sentence.lower()
            for keyword in deadline_keywords
        )
    ]

    # Common venue/location indicators.
    # English words must match as whole words ("at" must not match "that").
    venue_pattern = re.compile(
        r"\b(?:venue|location|room|hall|auditorium|lab|at)\b",
        flags=re.IGNORECASE
    )
    venue_keywords_devanagari = [
        "स्थळ", "ठिकाण", "स्थान", "कक्ष", "सभागृह"
    ]

    venue_sentences = [
        sentence
        for sentence in split_sentences(text)
        if venue_pattern.search(sentence)
        or any(keyword in sentence for keyword in venue_keywords_devanagari)
    ]

    # Common event indicators.
    event_keywords = [
        "workshop", "seminar", "competition", "meeting",
        "conference", "webinar", "event", "कार्यशाळा",
        "स्पर्धा", "बैठक", "परिषद", "कार्यक्रम", "सत्र"
    ]

    event_sentences = [
        sentence
        for sentence in split_sentences(text)
        if any(
            keyword in sentence.lower()
            for keyword in event_keywords
        )
    ]

    return {
        "dates": sorted(numeric_dates),
        "times": sorted(times),
        "phone_numbers": sorted(phone_numbers),
        "emails": sorted(emails),
        "deadlines": deadline_sentences,
        "venues": venue_sentences,
        "events": event_sentences,
    }


def structure_notice_text(text):
    """
    Organize translated notice text into meaningful sections.
    Uses lightweight multilingual keyword and regex rules.
    Does not generate or invent missing information.
    """

    text = clean_text(text)

    if not text:
        return {
            "title": "",
            "institution": [],
            "notice_date": [],
            "subject": [],
            "announcement": [],
            "important_dates": [],
            "instructions": [],
            "venue": [],
            "issued_by": [],
            "additional_details": []
        }

    lines = [
        line.strip(" \t•-*")
        for line in text.splitlines()
        if line.strip()
    ]

    sections = {
        "title": "",
        "institution": [],
        "notice_date": [],
        "subject": [],
        "announcement": [],
        "important_dates": [],
        "instructions": [],
        "venue": [],
        "issued_by": [],
        "additional_details": []
    }

    date_pattern = (
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"
        r"|\b\d{1,2}\.\d{1,2}\.\d{2,4}\b"
        r"|\b\d{1,2}\s+(?:January|February|March|April|May|June|"
        r"July|August|September|October|November|December)\s+\d{4}\b"
    )

    time_pattern = (
        r"\b\d{1,2}:\d{2}\s?(?:AM|PM)\b"
        r"|\b(?:[01]?\d|2[0-3]):[0-5]\d\b"
    )

    instruction_words = [
        "must", "required", "mandatory", "please bring",
        "submit", "carry", "attend",
        "अनिवार्य", "आवश्यक", "लाना होगा", "जमा करें",
        "करना आवश्यक", "करावे", "आवश्यक आहे",
        "अनिवार्य आहे", "सादर करावे"
    ]

    venue_words = [
        "venue", "location", "room no", "auditorium",
        "स्थळ", "ठिकाण", "सभागृह", "कक्ष"
    ]

    issuer_words = [
        "principal", "deputy principal", "head of department",
        "hod", "authorized signatory",
        "प्राचार्य", "उप प्राचार्य", "विभाग प्रमुख",
        "प्राचार्यांचे कार्यालय"
    ]

    institution_words = [
        "college", "university", "institute",
        "school", "महाविद्यालय", "विद्यापीठ",
        "संस्था", "विद्यालय"
    ]

    subject_words = [
        "subject:", "sub:", "विषय:", "विषय -"
    ]

    date_labels = [
        "date:", "dated:", "दिनांक:", "तारीख:"
    ]

    # Use the first short, heading-like line as the notice title.
    if lines:
        first = lines[0]
        if len(first) <= 70 and not re.search(r"[.!?।॥]$", first):
            sections["title"] = first
            lines = lines[1:]

    for line in lines:
        lower = line.lower()

        if any(word in lower for word in subject_words):
            sections["subject"].append(line)

        elif any(word in lower for word in date_labels):
            sections["notice_date"].append(line)

        elif any(word in lower for word in issuer_words):
            sections["issued_by"].append(line)

        elif any(word in lower for word in venue_words):
            sections["venue"].append(line)

        elif any(word in lower for word in institution_words):
            sections["institution"].append(line)

        elif re.search(date_pattern, line, re.IGNORECASE) or re.search(
            time_pattern, line, re.IGNORECASE
        ):
            sections["important_dates"].append(line)

        elif any(word in lower for word in instruction_words):
            sections["instructions"].append(line)

        else:
            sections["announcement"].append(line)

    # Keep all remaining content visible.
    if not sections["announcement"] and sections["additional_details"]:
        sections["announcement"] = sections["additional_details"]

    return sections


# --------------------------------------------------
# NLP: LANGUAGE DETECTION
# --------------------------------------------------

def predict_language(text):
    """Predict the most likely language for a text segment."""

    model = get_language_model()
    normalized = " ".join(text.split())

    if len(normalized) < 3:
        return None

    # fasttext_predict works with both NumPy 1 and NumPy 2.
    from nlp.multilingual import fasttext_predict

    predictions = []

    for label, probability in fasttext_predict(model, normalized, k=3):
        code = label.replace("__label__", "")

        predictions.append({
            "code": code,
            "name": LANGUAGE_NAMES.get(code, "Other language"),
            "confidence": round(float(probability), 4),
        })

    return predictions


def detect_languages(text, text_segments=None):
    """Detect dominant and mixed languages."""

    overall_predictions = predict_language(text)

    if not overall_predictions:
        return {
            "primary_language": "unknown",
            "primary_language_name": "Unknown",
            "confidence": 0.0,
            "is_mixed": False,
            "detected_languages": [],
            "language_distribution": {},
            "predictions": [],
        }

    overall_top = overall_predictions[0]
    language_weights = defaultdict(float)

    if text_segments:
        for segment in text_segments:
            segment = segment.strip()

            if len(segment) < 12:
                continue

            predictions = predict_language(segment)

            if not predictions:
                continue

            top_prediction = predictions[0]
            code = top_prediction["code"]
            confidence = top_prediction["confidence"]

            if (
                code in LANGUAGE_NAMES
                and confidence >= MIN_LANGUAGE_CONFIDENCE
            ):
                language_weights[code] += len(segment)

    if not language_weights:
        code = overall_top["code"]

        if code in LANGUAGE_NAMES:
            language_weights[code] = max(len(text), 1)

    total_weight = sum(language_weights.values())
    distribution = {}

    if total_weight:
        for code, weight in language_weights.items():
            distribution[LANGUAGE_NAMES[code]] = round(
                weight / total_weight * 100, 2
            )

        primary_code = max(
            language_weights,
            key=language_weights.get
        )
    else:
        primary_code = overall_top["code"]

    primary_name = LANGUAGE_NAMES.get(
        primary_code,
        "Other language"
    )

    significant_languages = [
        name
        for name, percentage in distribution.items()
        if percentage >= 10
    ]

    return {
        "primary_language": primary_code,
        "primary_language_name": primary_name,
        "confidence": overall_top["confidence"],
        "is_mixed": len(significant_languages) >= 2,
        "detected_languages": significant_languages,
        "language_distribution": distribution,
        "predictions": overall_predictions,
    }


# --------------------------------------------------
# OCR EXTRACTION
# --------------------------------------------------

def prepare_image_for_ocr(image_source):
    """
    Make a photo easier for OCR:
      1. rotate it upright using the phone's EXIF orientation,
      2. convert to grayscale and stretch the contrast,
      3. enlarge small photos (OCR misreads tiny letters) and shrink huge ones.

    image_source: a file path or PNG/JPG bytes. Returns a numpy array,
    or the original source if Pillow is not available.
    """

    try:
        import numpy as np
        from PIL import Image, ImageOps
    except ImportError:
        return image_source

    if isinstance(image_source, (bytes, bytearray)):
        image = Image.open(io.BytesIO(image_source))
    else:
        image = Image.open(image_source)

    image = ImageOps.exif_transpose(image)
    image = ImageOps.autocontrast(image.convert("L"), cutoff=1)

    long_side = max(image.size)
    if long_side < OCR_TARGET_LONG_SIDE:
        scale = min(OCR_TARGET_LONG_SIDE / long_side, 3)
    elif long_side > OCR_MAX_LONG_SIDE:
        scale = OCR_MAX_LONG_SIDE / long_side
    else:
        scale = 1

    if scale != 1:
        image = image.resize(
            (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
            Image.LANCZOS
        )

    return np.array(image)


def text_character_share(text):
    """
    Share of a line made of letters, digits or Devanagari vowel signs.
    "दिनांक 18/11" is high; "*-10*+7*" is low (OCR noise).
    """

    characters = [ch for ch in text if not ch.isspace()]
    if not characters:
        return 0.0

    useful = sum(
        1 for ch in characters
        if ch.isalnum() or unicodedata.category(ch).startswith("M")
    )
    return useful / len(characters)


def _ocr_lines(results, page_number=None):
    """
    Turn EasyOCR results [(box, text, confidence), ...] into line records,
    keeping only lines EasyOCR is reasonably sure about.

    Returns:
        (kept_lines, removed_count)
    """

    lines = []
    removed = 0

    for item in results:
        detected_text = item[1].strip()
        confidence = float(item[2])

        if not detected_text:
            continue

        if (
            confidence < MIN_OCR_CONFIDENCE
            or text_character_share(detected_text) < MIN_TEXT_CHARACTER_SHARE
        ):
            removed += 1
            continue

        lines.append({
            "text": detected_text,
            "ocr_confidence": round(confidence, 4),
            "page": page_number,
        })

    return lines, removed


def run_ocr(image_source, page_number=None):
    """Prepare the image, run EasyOCR, and filter the lines."""

    results = get_ocr_reader().readtext(
        prepare_image_for_ocr(image_source),
        detail=1,
        paragraph=False
    )
    return _ocr_lines(results, page_number)


def extract_image_text(image_path):
    """JPG/PNG: read the text with EasyOCR."""

    lines, removed = run_ocr(str(image_path))
    return {"lines": lines, "removed_lines": removed, "source_type": "image", "pages": 1}


def extract_pdf_text(pdf_path):
    """
    PDF: read each page's text layer directly (fast and exact).
    A page with almost no text is a scanned image, so it is rendered
    as a picture and read with EasyOCR instead.
    """

    try:
        import pymupdf
    except ImportError as error:
        raise NoticeDependencyError(
            "PyMuPDF is not installed, so PDFs cannot be read. "
            "Run: python -m pip install pymupdf"
        ) from error

    try:
        document = pymupdf.open(str(pdf_path))
    except Exception as error:
        raise ValueError("This PDF could not be opened. It may be damaged.") from error

    with document:
        if document.needs_pass:
            raise ValueError("Password-protected PDFs are not supported.")

        page_count = len(document)
        lines = []
        removed = 0
        text_pages = 0
        scanned_pages = 0

        for index in range(min(page_count, MAX_PDF_PAGES)):
            page = document[index]
            page_lines = [line.strip() for line in page.get_text("text").splitlines() if line.strip()]

            if len(" ".join(page_lines)) >= MIN_PAGE_TEXT_CHARS:
                text_pages += 1
                lines += [{"text": line, "ocr_confidence": None, "page": index + 1} for line in page_lines]
            else:
                scanned_pages += 1
                image_bytes = page.get_pixmap(dpi=PDF_OCR_DPI).tobytes("png")
                page_lines, page_removed = run_ocr(image_bytes, page_number=index + 1)
                lines += page_lines
                removed += page_removed

    if scanned_pages and text_pages:
        source_type = "pdf_mixed"
    elif scanned_pages:
        source_type = "pdf_scanned"
    else:
        source_type = "pdf_text"

    return {
        "lines": lines,
        "removed_lines": removed,
        "source_type": source_type,
        "pages": page_count,
        "pages_read": min(page_count, MAX_PDF_PAGES),
    }


def _word_paragraph_text(paragraph):
    """Text of one Word paragraph: its <w:t> runs, with tabs and line breaks kept."""

    parts = []
    for node in paragraph.iter():
        if node.tag == WORD_NAMESPACE + "t" and node.text:
            parts.append(node.text)
        elif node.tag == WORD_NAMESPACE + "tab":
            parts.append(" ")
        elif node.tag in (WORD_NAMESPACE + "br", WORD_NAMESPACE + "cr"):
            parts.append("\n")
    return "".join(parts)


def _word_xml_lines(xml_bytes):
    """Lines from one Word XML part, in reading order. Table rows become 'a | b | c'."""

    root = ET.fromstring(xml_bytes)
    body = root.find(WORD_NAMESPACE + "body")
    container = body if body is not None else root
    lines = []

    for block in container:
        if block.tag == WORD_NAMESPACE + "p":
            lines += _word_paragraph_text(block).split("\n")
        elif block.tag == WORD_NAMESPACE + "tbl":
            for row in block.iter(WORD_NAMESPACE + "tr"):
                cells = [
                    " ".join(_word_paragraph_text(p) for p in cell.iter(WORD_NAMESPACE + "p")).strip()
                    for cell in row.iter(WORD_NAMESPACE + "tc")
                ]
                lines.append(" | ".join(cell for cell in cells if cell))

    return [line.strip() for line in lines if line.strip()]


def extract_docx_text(docx_path):
    """
    DOCX: a Word file is a ZIP archive; the text is in word/document.xml
    (letterheads are often in word/header*.xml). Read with the standard
    library only, so no extra package is needed.
    """

    try:
        with zipfile.ZipFile(docx_path) as archive:
            names = archive.namelist()

            if "word/document.xml" not in names:
                raise ValueError("This is not a valid Word (.docx) file.")

            # Refuse oversized XML (protects against "zip bombs").
            if archive.getinfo("word/document.xml").file_size > 20 * 1024 * 1024:
                raise ValueError("This Word file is too large to process.")

            headers = sorted(name for name in names if re.fullmatch(r"word/header\d*\.xml", name))
            lines = []
            for part in headers + ["word/document.xml"]:
                lines += _word_xml_lines(archive.read(part))

    except zipfile.BadZipFile as error:
        raise ValueError("This Word file could not be read. Save it again as .docx.") from error
    except ET.ParseError as error:
        raise ValueError("This Word file is damaged and could not be read.") from error

    # A letterhead repeated on every page appears once.
    unique_lines = list(dict.fromkeys(lines))

    return {
        "lines": [{"text": line, "ocr_confidence": None, "page": None} for line in unique_lines],
        "source_type": "docx",
        "pages": None,
    }


def extract_notice_text(file_path):
    """
    Extract text from an uploaded notice: image, PDF or Word file.

    Returns:
        dict: text, segments (one per line, used for language detection),
              lines (with OCR confidence where OCR was used),
              source_type and page information.
    """

    file_path = Path(file_path)

    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = file_path.suffix.lower()

    if suffix == ".doc":
        raise ValueError("Old .doc files are not supported. Open it in Word and save as .docx or PDF.")

    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only JPG, PNG, PDF and DOCX files are supported.")

    if file_path.stat().st_size == 0:
        raise ValueError("The uploaded file is empty.")

    if file_path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("File size must not exceed 10 MB.")

    if suffix in IMAGE_EXTENSIONS:
        result = extract_image_text(file_path)
    elif suffix == ".pdf":
        result = extract_pdf_text(file_path)
    else:
        result = extract_docx_text(file_path)

    text_segments = [line["text"] for line in result["lines"]]
    full_text = preprocess_text("\n".join(text_segments))
    quality = ocr_quality(result["lines"], result.get("removed_lines", 0))

    if not full_text:
        if suffix in IMAGE_EXTENSIONS or quality["ocr_used"]:
            raise ValueError(
                "No readable text was detected. Try a sharper, straight, well-lit photo, "
                "or upload the original PDF if you have it."
            )
        raise ValueError("No text was found in this file.")

    return {
        "text": full_text,
        "segments": text_segments,
        "lines": result["lines"],
        "source_type": result["source_type"],
        "pages": result["pages"],
        "pages_read": result.get("pages_read"),
        "quality": quality,
    }


def ocr_quality(lines, removed_lines):
    """
    Summarise how trustworthy the OCR text is.
    Text read directly from a PDF/Word file has no OCR score and is trusted.
    """

    scores = [line["ocr_confidence"] for line in lines if line["ocr_confidence"] is not None]
    ocr_used = bool(scores) or removed_lines > 0

    if not ocr_used:
        return {"ocr_used": False, "average_confidence": None, "removed_lines": 0, "low": False}

    average = round(sum(scores) / len(scores), 4) if scores else 0.0
    kept = len(scores)
    low = average < LOW_QUALITY_CONFIDENCE or removed_lines > kept

    return {
        "ocr_used": True,
        "average_confidence": average,
        "kept_lines": kept,
        "removed_lines": removed_lines,
        "low": low,
    }


# --------------------------------------------------
# COMPLETE NOTICE PROCESSING
# --------------------------------------------------

def structure_notice_text(text):
    """Organize extracted notice text into meaningful sections."""

    text = clean_text(text)

    result = {
        "title": [],
        "institution": [],
        "notice_date": [],
        "subject": [],
        "announcement": [],
        "important_dates": [],
        "instructions": [],
        "venue": [],
        "issued_by": [],
        "additional_details": []
    }

    if not text:
        return result

    lines = [
        line.strip(" \t•-*|")
        for line in text.splitlines()
        if line.strip()
    ]

    instruction_keywords = [
        "must", "mandatory", "required", "please bring",
        "submit", "carry", "attend", "only candidates",
        "समय पर", "उपस्थित रहें", "अनिवार्य", "आवश्यक",
        "लाना होगा", "जमा करें", "करना आवश्यक",
        "करावे", "आवश्यक आहे", "सादर करावे",
        "केवल", "उम्मीदवारों को", "पालन करें"
    ]

    institution_keywords = [
        "college", "university", "institute",
        "महाविद्यालय", "विद्यापीठ", "संस्था",
        "कॉलेज", "विद्यालय"
    ]

    issuer_keywords = [
        "principal", "deputy principal", "hod",
        "head of department", "प्राचार्य",
        "उप-प्राचार्य", "उप प्राचार्य", "विभाग प्रमुख"
    ]

    venue_keywords = [
        "venue", "location", "room no",
        "auditorium", "स्थळ", "ठिकाण",
        "सभागृह", "कक्ष"
    ]

    subject_keywords = [
        "subject:", "sub:", "विषय:", "विषय -",
        "ba ll.b", "b.a. ll.b", "admission",
        "प्रवेश", "परीक्षा", "कार्यक्रम"
    ]

    date_label_keywords = [
        "date", "dated", "दिनांक",
        "तारीख", "सूचना दिनांक"
    ]

    date_pattern = r"\b\d{1,2}\s*[./-]\s*\d{1,2}\s*[./-]\s*\d{2,4}\b"
    time_pattern = r"\b\d{1,2}\s*[:.]\s*\d{2}\s*(?:AM|PM|am|pm)?\b"

    title_keywords = ["notice", "सूचना", "जाहिर सूचना", "नोटीस"]

    for index, line in enumerate(lines):

        lower = line.lower()

        if any(word in lower for word in title_keywords):
            result["title"].append(line)

        elif any(word in lower for word in date_label_keywords):
            result["notice_date"].append(line)

        elif any(word in lower for word in issuer_keywords):
            result["issued_by"].append(line)

        elif any(word in lower for word in institution_keywords):
            result["institution"].append(line)

        elif any(word in lower for word in venue_keywords):
            result["venue"].append(line)

        elif any(word in lower for word in instruction_keywords):
            result["instructions"].append(line)

        elif re.search(date_pattern, line) or re.search(time_pattern, line):
            result["important_dates"].append(line)

        elif any(word in lower for word in subject_keywords):
            result["subject"].append(line)

        elif index == 0 and len(line) < 100:
            result["additional_details"].append(line)

        else:
            result["announcement"].append(line)

    for key in result:
        result[key] = list(dict.fromkeys(result[key]))

    return result

def process_notice(image_path):
    """
    Complete pipeline:
    Image/PDF/DOCX -> text (OCR or direct) -> Preprocessing -> Language detection
    -> Sentence segmentation -> Information extraction
    """

    ocr_result = extract_notice_text(image_path)

    processed_text = preprocess_text(ocr_result["text"])

    language_result = detect_languages(
        processed_text,
        ocr_result["segments"]
    )

    sentences = split_sentences(processed_text)
    extracted_information = extract_information(processed_text)
    structured_notice = structure_notice_text(processed_text)

    return {
        "success": True,
        "extracted_text": processed_text,
        "source_type": ocr_result["source_type"],
        "quality": ocr_result["quality"],
        "pages": ocr_result["pages"],
        "pages_read": ocr_result["pages_read"],
        "lines": ocr_result["lines"],
        "language": language_result,
        "nlp": {
            "sentences": sentences,
            "sentence_count": len(sentences),
            "information": extracted_information,
        },
        "structured_notice": structured_notice,
        "message": "Notice processed successfully."
    }


def structure_notice_text(text):
    """Organize OCR text into notice sections without inventing details."""

    text = clean_text(text)

    result = {
        "title": [],
        "institution": [],
        "notice_date": [],
        "subject": [],
        "announcement": [],
        "important_dates": [],
        "instructions": [],
        "venue": [],
        "issued_by": [],
        "additional_details": []
    }

    if not text:
        return result

    lines = [
        line.strip(" \t•-*|")
        for line in text.splitlines()
        if line.strip()
    ]

    instruction_keywords = [
        "must", "mandatory", "required", "please bring",
        "submit", "carry", "attend", "only candidates",
        "अनिवार्य", "आवश्यक", "लाना होगा", "जमा करें",
        "करना आवश्यक", "करावे", "आवश्यक आहे",
        "अनिवार्य आहे", "सादर करावे", "केवल",
        "उम्मीदवारों को", "पालन करें"
    ]

    institution_keywords = [
        "college", "university", "institute",
        "महाविद्यालय", "विद्यापीठ", "संस्था",
        "कॉलेज", "विद्यालय"
    ]

    issuer_keywords = [
        "principal", "deputy principal", "hod",
        "head of department", "प्राचार्य",
        "उप-प्राचार्य", "उप प्राचार्य",
        "विभाग प्रमुख"
    ]

    venue_keywords = [
        "venue", "location", "room no", "auditorium",
        "स्थळ", "ठिकाण", "सभागृह", "कक्ष"
    ]

    subject_keywords = [
        "subject:", "sub:", "विषय:", "विषय -",
        "ba ll.b", "b.a. ll.b", "admission",
        "प्रवेश", "परीक्षा", "कार्यक्रम"
    ]

    date_label_keywords = [
        "date:", "dated:", "दिनांक:", "तारीख:",
        "सूचना दिनांक"
    ]

    date_pattern = (
        r"\b\d{1,2}\s*[./-]\s*\d{1,2}\s*[./-]\s*\d{2,4}\b"
    )

    time_pattern = (
        r"\b\d{1,2}\s*[:.]\s*\d{2}\s*(?:AM|PM|am|pm)?\b"
    )

    title_keywords = [
        "notice", "सूचना", "जाहिर सूचना", "नोटीस"
    ]

    for index, line in enumerate(lines):
        lower = line.lower()

        if any(word in lower for word in title_keywords):
            result["title"].append(line)

        elif any(word in lower for word in date_label_keywords):
            result["notice_date"].append(line)

        elif any(word in lower for word in issuer_keywords):
            result["issued_by"].append(line)

        elif any(word in lower for word in institution_keywords):
            result["institution"].append(line)

        elif any(word in lower for word in venue_keywords):
            result["venue"].append(line)

        elif re.search(date_pattern, line) or re.search(
            time_pattern, line
        ):
            result["important_dates"].append(line)

        elif any(word in lower for word in instruction_keywords):
            result["instructions"].append(line)

        elif any(word in lower for word in subject_keywords):
            result["subject"].append(line)

        elif index == 0 and len(line) < 100:
            result["additional_details"].append(line)

        else:
            result["announcement"].append(line)

    # Remove repeated OCR lines without changing their content.
    for key, values in result.items():
        result[key] = list(dict.fromkeys(values))

    return result

# --------------------------------------------------
# MACHINE TRANSLATION - MYMEMORY API
# --------------------------------------------------

import json
import html
import urllib.parse
import urllib.request
import urllib.error


TRANSLATION_API_URL = "https://api.mymemory.translated.net/get"

SUPPORTED_TRANSLATION_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
}


def split_translation_chunks(text, max_bytes=450):
    """
    Split long text into smaller chunks.
    MyMemory allows a maximum of 500 bytes per request.
    """

    sentences = split_sentences(text)

    chunks = []
    current_chunk = ""

    for sentence in sentences:

        sentence_size = len(sentence.encode("utf-8"))

        # Handle unusually long sentences.
        if sentence_size > max_bytes:

            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""

            words = sentence.split()
            word_chunk = ""

            for word in words:

                candidate = (
                    word_chunk + " " + word
                    if word_chunk else word
                )

                if len(candidate.encode("utf-8")) > max_bytes:

                    if word_chunk:
                        chunks.append(word_chunk)

                    if len(word.encode("utf-8")) > max_bytes:
                        raise ValueError(
                            "A single word is too large to translate."
                        )

                    word_chunk = word

                else:
                    word_chunk = candidate

            if word_chunk:
                chunks.append(word_chunk)

            continue

        candidate = (
            current_chunk + " " + sentence
            if current_chunk else sentence
        )

        if len(candidate.encode("utf-8")) > max_bytes:

            if current_chunk:
                chunks.append(current_chunk)

            current_chunk = sentence

        else:
            current_chunk = candidate

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def translate_text(text, source_language, target_language):
    """
    Translate text using the free MyMemory API.

    Supported language codes:
    en = English
    hi = Hindi
    mr = Marathi

    No API key or local translation model required.
    """

    text = preprocess_text(text)

    if not text:
        raise ValueError("There is no text available to translate.")

    if source_language not in SUPPORTED_TRANSLATION_LANGUAGES:
        raise ValueError(
            "Unsupported source language: " + str(source_language)
        )

    if target_language not in SUPPORTED_TRANSLATION_LANGUAGES:
        raise ValueError(
            "Unsupported target language: " + str(target_language)
        )

    if source_language == target_language:
        return {
            "success": True,
            "translated_text": text,
            "source_language": source_language,
            "target_language": target_language,
            "provider": "MyMemory",
            "message": "Source and target languages are the same."
        }

    chunks = split_translation_chunks(text)
    translated_chunks = []

    for chunk in chunks:

        parameters = {
            "q": chunk,
            "langpair": f"{source_language}|{target_language}",
            "mt": "1",
        }

        query_string = urllib.parse.urlencode(parameters)

        request_url = TRANSLATION_API_URL + "?" + query_string

        request = urllib.request.Request(
            request_url,
            headers={
                "User-Agent": "StudyMateAI-NoticeTranslator/1.0"
            }
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=20
            ) as response:

                result = json.loads(
                    response.read().decode("utf-8")
                )

        except urllib.error.HTTPError as error:
            raise RuntimeError(
                f"Translation service returned HTTP {error.code}."
            ) from error

        except urllib.error.URLError as error:
            raise RuntimeError(
                "Unable to connect to the translation service. "
                "Check your internet connection."
            ) from error

        except TimeoutError as error:
            raise RuntimeError(
                "Translation request timed out. Please try again."
            ) from error

        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise RuntimeError(
                "Invalid response received from translation service."
            ) from error

        if result.get("responseStatus") != 200:
            error_message = result.get(
                "responseDetails",
                "Translation failed."
            )

            raise RuntimeError(str(error_message))

        translated = result.get(
            "responseData", {}
        ).get("translatedText", "")

        translated = html.unescape(translated).strip()

        if not translated:
            raise RuntimeError(
                "The translation service returned empty text."
            )

        translated_chunks.append(translated)

    return {
        "success": True,
        "translated_text": "\n".join(translated_chunks),
        "source_language": source_language,
        "source_language_name": SUPPORTED_TRANSLATION_LANGUAGES[
            source_language
        ],
        "target_language": target_language,
        "target_language_name": SUPPORTED_TRANSLATION_LANGUAGES[
            target_language
        ],
        "provider": "MyMemory",
        "chunks_translated": len(translated_chunks),
        "message": "Translation completed successfully."
    }


def translate_notice(notice_text, target_language, source_language=None):
    """
    Translate an extracted college notice.

    If source_language is not provided, detect it automatically.
    """

    if not source_language:
        detection = detect_languages(notice_text)
        source_language = detection["primary_language"]

    return translate_text(
        text=notice_text,
        source_language=source_language,
        target_language=target_language
    )
