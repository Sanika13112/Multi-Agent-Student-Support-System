
"""
StudyMate AI - QuickNotes Service

MODE 1: QUICK NOTES
- Python-based processing
- Content classification
- Topic-wise organization
- Definitions, formulas, examples and algorithms
- Original PDF vector diagram previews
- Generated Mermaid diagrams
- No AI model calls

MODE 2: AI DETAILED NOTES
- Document cleaning
- TF-IDF content selection
- One Qwen2.5:3B generation call
- Original PDF vector diagram previews
- Generated Mermaid diagrams
- Exam-oriented structured notes
"""

import re
from pathlib import Path
from collections import Counter

from sklearn.feature_extraction.text import TfidfVectorizer

from modules.common.document_loader import load_document
from modules.common.utils import (
    format_file_size,
    calculate_file_hash,
    chunk_text
)
from modules.common.ai_client import generate_response

from modules.quick_notes.content_classifier import classify_document
from modules.quick_notes.diagram_extractor import extract_original_diagrams
from modules.quick_notes.diagram_generator import generate_diagrams
from modules.quick_notes.formatter import format_study_notes


# ==================================================
# CONFIGURATION
# ==================================================

MODEL_NAME = "qwen2.5:3b"

CHUNK_SIZE = 8000
CHUNK_OVERLAP = 300

MAX_SELECTED_SENTENCES = 65
MAX_INPUT_CHARACTERS = 9000

MAX_OUTPUT_TOKENS = 900


# ==================================================
# 1. DOCUMENT PREPARATION
# ==================================================

def prepare_study_document(file_path, extract_diagrams=True):
    """
    Load and prepare PDF or TXT documents.

    Original diagrams:
        Only vector-heavy page previews are included.
        Individual embedded icons and decorative images
        are excluded.

    The same original diagrams are used in both modes.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Document not found: {path}"
        )

    if path.suffix.lower() not in [".pdf", ".txt"]:
        raise ValueError(
            "Only PDF and TXT files are supported."
        )

    document = load_document(path)

    if not isinstance(document, dict):
        raise ValueError(
            "Document loader returned an unexpected result."
        )

    document_text = document.get("text", "")

    if not document_text or not document_text.strip():
        raise ValueError(
            "No readable content found in document."
        )

    file_size = path.stat().st_size
    file_hash = calculate_file_hash(path)

    cleaned_text = clean_document_text(document_text)

    if not cleaned_text:
        raise ValueError(
            "No readable content found after cleaning."
        )

    text_chunks = chunk_text(
        cleaned_text,
        chunk_size=CHUNK_SIZE,
        overlap=CHUNK_OVERLAP
    )

    original_diagrams = []
    diagram_result = None
    preparation_warnings = []

    # Diagram extraction is optional: a PDF rendering issue should
    # not prevent students from receiving their notes.
    if extract_diagrams and path.suffix.lower() == ".pdf":
        try:
            diagram_result = extract_original_diagrams(path)
            # Preserve the existing behaviour: include vector-heavy
            # page previews, not small decorative embedded images.
            original_diagrams = diagram_result.get(
                "vector_previews",
                []
            )
        except Exception as exc:
            preparation_warnings.append(
                f"Diagram extraction was skipped: {type(exc).__name__}"
            )

    provenance = {
        "filename": document.get("filename", path.name),
        "file_size_bytes": file_size,
        "file_size_readable": format_file_size(file_size),
        "sha256": file_hash
    }

    return {
        "success": True,
        "filename": document.get("filename", path.name),
        "file_type": document.get(
            "file_type",
            path.suffix.lower()
        ),
        "page_count": document.get("page_count", 0),
        "text": cleaned_text,
        "chunks": text_chunks,
        "chunk_count": len(text_chunks),
        "original_diagrams": original_diagrams,
        "diagram_result": diagram_result,
        "provenance": provenance,
        "warnings": preparation_warnings
    }


# ==================================================
# 2. DOCUMENT TEXT CLEANING
# ==================================================

def clean_document_text(text):
    """Clean PDF/TXT extraction artifacts."""

    if not text:
        return ""

    text = text.replace("\ufb01", "fi")
    text = text.replace("\ufb02", "fl")
    text = text.replace("\u00a0", " ")
    text = text.replace("\u2011", "-")
    text = text.replace("\x00", " ")

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    normalized_lines = [
        re.sub(r"\s+", " ", line).strip().lower()
        for line in lines
    ]

    line_counts = Counter(normalized_lines)

    cleaned_lines = []

    for line, normalized in zip(lines, normalized_lines):

        # Remove standalone page numbers.
        if re.fullmatch(r"[-–—]?\s*\d{1,3}\s*[-–—]?", line):
            continue

        # Remove repeated headers and footers.
        if line_counts[normalized] >= 3 and len(line) < 130:
            continue

        # Remove spaced-out uppercase artifacts.
        if re.search(r"(?:[A-Z]\s+){5,}[A-Z]", line):
            continue

        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)

    # Join words split by hyphen at line endings.
    text = re.sub(r"-\n(?=[a-z])", "", text)

    # Normalize whitespace.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ==================================================
# 3. SENTENCE SPLITTING
# ==================================================

def split_into_sentences(text):
    """Split text while preserving source order."""

    if not text:
        return []

    parts = re.split(
        r"(?<=[.!?])\s+(?=[A-Z0-9(])|\n+",
        text
    )

    sentences = []

    for part in parts:

        part = part.strip()

        if len(part) < 20:
            continue

        if re.fullmatch(r"[\W\d_]+", part):
            continue

        sentences.append(part)

    return sentences


# ==================================================
# 4. HEADING AND TOPIC DETECTION
# ==================================================

def is_heading(line):
    """Identify likely educational topic headings."""

    line = line.strip()

    if not line or len(line) > 110:
        return False

    if len(line.split()) > 14:
        return False

    # Numbered headings.
    if re.match(
        r"^(?:unit\s+\d+|chapter\s+\d+|\d+(?:\.\d+)*[.)]?\s+\D)",
        line,
        re.IGNORECASE
    ):
        return True

    # Common educational headings.
    if re.match(
        r"^(introduction|conclusion|overview|applications|"
        r"definition|properties|characteristics|advantages|"
        r"disadvantages|algorithm|example|summary|"
        r"important concepts|real-life applications|"
        r"computational complexity|complexity classes|"
        r"polynomial time|np-complete|np-hard|vertex cover|"
        r"approximation algorithm|satisfiability|"
        r"polynomial-time reduction)\b",
        line,
        re.IGNORECASE
    ):
        return True

    # Short labels ending in a colon.
    if line.endswith(":") and len(line.split()) <= 8:
        return True

    # Short title-like lines.
    if (
        len(line.split()) <= 6
        and not re.search(r"[.!?]$", line)
        and line[0].isupper()
        and not re.match(
            r"^(what|why|how)\s*:",
            line,
            re.IGNORECASE
        )
    ):
        return True

    return False


def extract_topic_sections(text):
    """Group document lines under likely topic headings."""

    sections = []

    current_heading = "General Concepts"
    current_content = []

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        if is_heading(line):

            if current_content:

                sections.append({
                    "heading": current_heading,
                    "content": current_content
                })

            current_heading = line.rstrip(":")
            current_content = []

        else:

            current_content.append(line)

    if current_content:

        sections.append({
            "heading": current_heading,
            "content": current_content
        })

    return sections


# ==================================================
# 5. TF-IDF IMPORTANT SENTENCE SELECTION
# ==================================================

def select_important_sentences(document_text):
    """Select important sentences using TF-IDF."""

    sentences = split_into_sentences(document_text)

    if not sentences:
        return ""

    if len(sentences) <= MAX_SELECTED_SENTENCES:

        return "\n".join(sentences)[:MAX_INPUT_CHARACTERS]

    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=4000,
        ngram_range=(1, 2)
    )

    try:

        matrix = vectorizer.fit_transform(sentences)
        scores = matrix.sum(axis=1).A1

    except ValueError:

        return document_text[:MAX_INPUT_CHARACTERS]

    important_patterns = [
        r"\bdefinition\b",
        r"\bdefined as\b",
        r"\bwhat\s*:",
        r"\bmeans\b",
        r"\brefers to\b",
        r"\bformula\b",
        r"\bequation\b",
        r"\btheorem\b",
        r"\balgorithm\b",
        r"\bcomplexity\b",
        r"\bexample\b",
        r"\badvantages?\b",
        r"\bdisadvantages?\b",
        r"\bproperties\b",
        r"\bapplications?\b",
        r"\bcharacteristics?\b",
        r"\bguarantee\b",
        r"\bsteps?\b"
    ]

    for index, sentence in enumerate(sentences):

        lower_sentence = sentence.lower()

        for pattern in important_patterns:

            if re.search(pattern, lower_sentence):

                scores[index] *= 1.5
                break

        if (
            re.search(r"[=<>±∑∫√∞]", sentence)
            and len(sentence) < 180
        ):

            scores[index] *= 1.3

    ranked_indices = sorted(
        range(len(sentences)),
        key=lambda index: scores[index],
        reverse=True
    )

    selected_indices = []
    selected_length = 0

    for index in ranked_indices:

        sentence = sentences[index]

        if len(selected_indices) >= MAX_SELECTED_SENTENCES:
            break

        if selected_length + len(sentence) > MAX_INPUT_CHARACTERS:
            continue

        selected_indices.append(index)
        selected_length += len(sentence)

    # Restore original document order.
    selected_indices.sort()

    return "\n".join(
        sentences[index]
        for index in selected_indices
    )


# ==================================================
# 6. DIAGRAM MARKDOWN HELPERS
# ==================================================

def build_diagram_markdown(
    original_diagrams=None,
    generated_diagrams=None
):
    """
    Convert original vector previews and generated
    Mermaid diagrams into Markdown.
    """

    sections = []

    original_diagrams = original_diagrams or []
    generated_diagrams = generated_diagrams or []

    # ----------------------------------------------
    # ORIGINAL PDF DIAGRAMS
    # ----------------------------------------------

    valid_original_diagrams = [
        diagram
        for diagram in original_diagrams
        if isinstance(diagram, dict) and diagram.get("url")
    ]

    if valid_original_diagrams:

        sections.append("## Original Diagrams\n")

        for index, diagram in enumerate(
            valid_original_diagrams,
            start=1
        ):

            image_url = diagram.get("url")

            filename = diagram.get(
                "filename",
                f"Diagram {index}"
            )

            page = diagram.get("page", "Unknown")

            sections.append(
                f"### Page {page}\n\n"
                f"![{filename}]({image_url})\n"
            )

    # ----------------------------------------------
    # GENERATED MERMAID DIAGRAMS
    # ----------------------------------------------

    valid_generated_diagrams = []

    for index, diagram in enumerate(generated_diagrams, 1):

        if isinstance(diagram, str):

            title = f"Generated Diagram {index}"
            mermaid_code = diagram

        elif isinstance(diagram, dict):

            title = (
                diagram.get("title")
                or diagram.get("name")
                or f"Generated Diagram {index}"
            )

            mermaid_code = (
                diagram.get("code")
                or diagram.get("mermaid")
                or diagram.get("content")
                or diagram.get("diagram")
                or ""
            )

        else:
            continue

        if not isinstance(mermaid_code, str):
            continue

        mermaid_code = mermaid_code.strip()

        if not mermaid_code:
            continue

        # Remove existing Mermaid fences.
        mermaid_code = re.sub(
            r"^\s*```(?:mermaid)?\s*|\s*```\s*$",
            "",
            mermaid_code,
            flags=re.IGNORECASE
        ).strip()

        if mermaid_code:

            valid_generated_diagrams.append(
                (title, mermaid_code)
            )

    if valid_generated_diagrams:

        sections.append("## Generated Diagrams\n")

        for title, mermaid_code in valid_generated_diagrams:

            sections.append(
                f"### {title}\n\n"
                f"```mermaid\n"
                f"{mermaid_code}\n"
                f"```\n"
            )

    return "\n".join(sections)


def append_diagrams_to_notes(
    notes,
    original_diagrams=None,
    generated_diagrams=None
):
    """Append diagram sections to generated study notes."""

    diagram_markdown = build_diagram_markdown(
        original_diagrams=original_diagrams,
        generated_diagrams=generated_diagrams
    )

    if not diagram_markdown:
        return notes

    return (
        notes.rstrip()
        + "\n\n"
        + diagram_markdown
    )


# ==================================================
# 7. DUPLICATE REMOVAL
# ==================================================

def remove_duplicates(items):
    """Remove duplicate text while preserving order."""

    result = []
    seen = set()

    for item in items:

        if not isinstance(item, str):
            continue

        normalized = re.sub(
            r"\s+",
            " ",
            item
        ).strip().lower()

        if normalized and normalized not in seen:

            seen.add(normalized)
            result.append(item.strip())

    return result


# ==================================================
# 8. QUICK NOTES - PYTHON ONLY
# ==================================================

def generate_quick_notes(
    document_text,
    filename="Study Document",
    original_diagrams=None
):
    """
    Generate improved structured study notes using Python.

    No Ollama or Qwen calls are made.

    The source content is preserved and organized
    into topic-wise sections.
    """

    if not isinstance(document_text, str) or not document_text.strip():

        raise ValueError(
            "Document text cannot be empty."
        )

    # 1. Clean document text.
    cleaned_text = clean_document_text(document_text)

    # 2. Classify document content.
    classified_content = classify_document(cleaned_text)

    # 3. Extract topic-wise content.
    detected_sections = extract_topic_sections(cleaned_text)

    topic_sections = {}

    for section in detected_sections:

        heading = section.get(
            "heading",
            "General Concepts"
        )

        content = section.get("content", [])

        if not content:
            continue

        # Preserve complete source sentences and lines.
        topic_text = "\n\n".join(
            line.strip()
            for line in content
            if line.strip()
        )

        if heading in topic_sections:

            topic_sections[heading] += (
                "\n\n" + topic_text
            )

        else:

            topic_sections[heading] = topic_text

    # 4. Generate diagrams locally.
    generated_diagrams = generate_diagrams(cleaned_text)

    original_diagrams = original_diagrams or []

    # 5. Remove duplicate extracted content.
    for key in [
        "definitions",
        "examples",
        "formulas",
        "algorithms",
        "important_points"
    ]:

        classified_content[key] = remove_duplicates(
            classified_content.get(key, [])
        )

    # 6. Format complete study notes.
    notes = format_study_notes(
        document_name=filename,
        classified_content=classified_content,
        original_diagrams=original_diagrams,
        generated_diagrams=generated_diagrams,
        topic_sections=topic_sections
    )

    # 7. Return result.
    return {
        "success": True,
        "filename": filename,
        "notes": notes,
        "sections_processed": len(topic_sections),
        "model": "Python Rules",
        "processing_method": "Fast Python-Based Extraction",
        "source_characters": len(document_text),
        "selected_characters": len(cleaned_text),
        "original_diagram_count": len(original_diagrams),
        "generated_diagram_count": len(generated_diagrams),
        "original_diagrams": original_diagrams,
        "generated_diagrams": generated_diagrams,
        "warnings": []
    }


# ==================================================
# 9. AI DETAILED NOTES - QWEN
# ==================================================

def generate_detailed_notes(
    document_text,
    filename="Study Document",
    original_diagrams=None
):
    """
    Generate detailed exam-oriented notes using Qwen.

    Makes one AI generation call.

    Original vector previews and generated Mermaid
    diagrams are appended after AI note generation.
    """

    if not isinstance(document_text, str) or not document_text.strip():

        raise ValueError(
            "Document text cannot be empty."
        )

    cleaned_text = clean_document_text(document_text)

    # Select relevant content.
    selected_text = select_important_sentences(cleaned_text)

    if not selected_text.strip():

        raise ValueError(
            "Unable to select meaningful document content."
        )

    system_prompt = """
You are QuickNotes, an expert study assistant for B.Tech students.

Create structured, detailed and exam-oriented study notes.

Use ONLY the supplied source content.

Organize the notes into:

1. Document Overview
2. Topic-Wise Notes
3. Important Concepts
4. Important Definitions
5. Key Points
6. Technical Terms
7. Important Formulas and Equations
8. Algorithms and Steps
9. Examples
10. Quick Revision Notes

Rules:

- Use simple English.
- Preserve the original topic sequence.
- Explain concepts clearly using source-supported information.
- Preserve technical terminology.
- Include formulas only when supported by the source.
- Explain formulas when sufficient information exists.
- Use headings, numbered steps and bullet points.
- Avoid unnecessary repetition.
- Do not invent information.
- Do not add unrelated concepts.
- Mention when information is unavailable.
- Focus on B.Tech examination preparation.
- Prefer clear and concise explanations.
- Do not claim that a formula, example, theorem or algorithm appears
  in the source unless it is present in the supplied text.
- If a topic is only named but not explained, state that the source
  provides limited detail instead of inventing an explanation.
- Preserve important conditions, assumptions and complexity notation.
- Do not omit relevant steps from algorithms included in the source.
- Use Markdown tables only when they improve comparison.
"""

    prompt = f"""
Document name: {filename}

Source content:

{selected_text}

Generate the detailed study notes.
"""

    # One Qwen generation call.
    ai_notes = generate_response(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.2,
        max_tokens=MAX_OUTPUT_TOKENS
    )

    if not isinstance(ai_notes, str) or not ai_notes.strip():

        raise RuntimeError(
            "Qwen returned an empty or invalid response."
        )

    # Generate diagrams locally using Python.
    # No additional AI call.
    generated_diagrams = generate_diagrams(cleaned_text)

    original_diagrams = original_diagrams or []

    # Append original and generated diagrams.
    final_notes = append_diagrams_to_notes(
        notes=ai_notes.strip(),
        original_diagrams=original_diagrams,
        generated_diagrams=generated_diagrams
    )

    return {
        "success": True,
        "filename": filename,
        "notes": final_notes,
        "sections_processed": 1,
        "model": MODEL_NAME,
        "processing_method": "TF-IDF + Qwen AI + Python Diagrams",
        "source_characters": len(document_text),
        "selected_characters": len(selected_text),
        "original_diagram_count": len(original_diagrams),
        "generated_diagram_count": len(generated_diagrams),
        "original_diagrams": original_diagrams,
        "generated_diagrams": generated_diagrams,
        "warnings": []
    }
