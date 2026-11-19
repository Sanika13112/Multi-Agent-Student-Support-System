
"""
QuickNotes - Improved Content Classifier

Extracts:
1. Definitions
2. Examples
3. Formulas
4. Algorithms
5. Important points

Uses Python and Regex only.
No AI model required.
"""

import re


# --------------------------------------------------
# TEXT CLEANING
# --------------------------------------------------

IGNORE_PATTERNS = [
    r"design and analysis of algorithms",
    r"unit\s*\d+",
    r"page\s*\d+",
    r"total\s*:",
    r"^output$",
    r"^input$",
]


def clean_text(text):
    """Clean extracted PDF text without removing technical content."""

    if not isinstance(text, str):
        return ""

    text = text.replace("\x00", " ")
    text = text.replace("\r", "\n")
    text = text.replace("\u00a0", " ")

    # Fix common PDF ligatures
    text = text.replace("\ufb01", "fi")
    text = text.replace("\ufb02", "fl")

    # Join words broken across PDF lines
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)

    # Normalize spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Normalize excessive newlines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# --------------------------------------------------
# LINE AND SENTENCE EXTRACTION
# --------------------------------------------------

def get_lines(text):
    """Return cleaned non-empty lines."""

    return [
        line.strip()
        for line in clean_text(text).splitlines()
        if line.strip()
    ]


def get_sentences(text):
    """
    Reconstruct sentences from PDF text.

    Joins wrapped PDF lines while preserving headings,
    bullet points and numbered items.
    """

    lines = get_lines(text)

    paragraphs = []
    current = []

    def save_current():
        if current:
            paragraphs.append(" ".join(current).strip())
            current.clear()

    for line in lines:

        # Preserve headings and numbered sections
        is_heading = (
            len(line) <= 110
            and (
                re.match(
                    r"^(?:\d+(?:\.\d+)*[.)]?\s+|chapter\s+\d+|unit\s+\d+)",
                    line,
                    re.IGNORECASE
                )
                or line.endswith(":")
            )
        )

        # Preserve bullets and numbered steps
        is_list_item = re.match(
            r"^(?:[-•*]\s+|\d+[.)]\s+|step\s+\d+)",
            line,
            re.IGNORECASE
        )

        if is_heading or is_list_item:
            save_current()
            paragraphs.append(line)
            continue

        current.append(line)

        # A sentence-ending line usually finishes a paragraph.
        # Avoid splitting common abbreviations.
        if re.search(r'[.!?]["\')\]]?$', line):
            save_current()

    save_current()

    sentences = []

    for paragraph in paragraphs:

        if not paragraph:
            continue

        # Do not split headings or list items unnecessarily
        if re.match(
            r"^(?:[-•*]\s+|\d+[.)]\s+|step\s+\d+)",
            paragraph,
            re.IGNORECASE
        ):
            parts = [paragraph]
        else:
            parts = re.split(
                r'(?<=[.!?])\s+(?=[A-Z0-9])',
                paragraph
            )

        for part in parts:
            part = re.sub(r"\s+", " ", part).strip()

            if len(part) >= 20:
                sentences.append(part)

    return sentences


# --------------------------------------------------
# VALIDATION
# --------------------------------------------------

def is_irrelevant(line):
    """Remove common PDF headers, footers and fragments."""

    if not isinstance(line, str):
        return True

    lower = line.lower().strip()

    if len(lower) < 20:
        return True

    for pattern in IGNORE_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            return True

    if lower.startswith(("why:", "what:", "total:")):
        return True

    # Reject lines containing only page-number information
    if re.fullmatch(r"[\d\s|./-]+", lower):
        return True

    return False


def is_complete_sentence(sentence):
    """Check whether a sentence appears reasonably complete."""

    if not isinstance(sentence, str):
        return False

    sentence = sentence.strip()

    if len(sentence.split()) < 5:
        return False

    # Allow technical statements ending without punctuation
    # when they are clearly labelled list items.
    labelled_item = bool(
        re.match(
            r"^(?:[-•*]\s+|\d+[.)]\s+|step\s+\d+)",
            sentence,
            re.IGNORECASE
        )
    )

    if not re.search(r'[.!?]["\')\]]?$', sentence) and not labelled_item:
        return False

    incomplete_endings = (
        "and", "or", "but", "because", "with", "of",
        "to", "for", "in", "on", "at", "by", "from",
        "such as", "as well as", "the", "a", "an",
        "is", "are", "can", "will", "would", "which"
    )

    body = re.sub(r'[.!?]+$', '', sentence.lower()).strip()

    if any(body.endswith(" " + ending) for ending in incomplete_endings):
        return False

    return True


# --------------------------------------------------
# REMOVE DUPLICATES
# --------------------------------------------------

def remove_duplicates(items):
    """Remove repeated text while preserving original order."""

    seen = set()
    result = []

    for item in items:

        if not isinstance(item, str):
            continue

        item = item.strip()
        normalized = re.sub(r"\s+", " ", item.lower())

        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(item)

    return result


# --------------------------------------------------
# DEFINITIONS
# --------------------------------------------------

def extract_definitions(text):
    """Extract complete definition statements."""

    definitions = []

    patterns = [
        r"\bis defined as\b",
        r"\bare defined as\b",
        r"\bcan be defined as\b",
        r"\brefers to\b",
        r"\bis known as\b",
        r"\bare known as\b",
        r"\bmeans\b",
        r"\bis a type of\b",
        r"\bis the process of\b",
        r"\bis a method of\b",
        r"\bis a technique for\b",
        r"\bis an approach to\b",
        r"\bconsists of\b",
    ]

    for sentence in get_sentences(text):

        if is_irrelevant(sentence):
            continue

        if not is_complete_sentence(sentence):
            continue

        if any(
            re.search(pattern, sentence, re.IGNORECASE)
            for pattern in patterns
        ):
            definitions.append(sentence)

    return remove_duplicates(definitions)


# --------------------------------------------------
# EXAMPLES
# --------------------------------------------------

def extract_examples(text):
    """Extract explicitly labelled examples."""

    examples = []

    pattern = re.compile(
        r"^(?:[-•*]\s*)?(?:example|for example|for instance)"
        r"\s*(?:\d+)?\s*[:.)-]?\s*",
        re.IGNORECASE
    )

    for sentence in get_sentences(text):

        if is_irrelevant(sentence):
            continue

        if not pattern.match(sentence):
            continue

        # Keep labelled examples even when the PDF uses
        # a list-style format without final punctuation.
        if len(sentence.split()) >= 5:
            examples.append(sentence)

    return remove_duplicates(examples)


# --------------------------------------------------
# FORMULAS
# --------------------------------------------------

def extract_formulas(text):
    """Extract likely mathematical expressions and equations."""

    formulas = []

    patterns = [
        # Variable assignments: T(n) = n^2
        r"\b[A-Za-z_][A-Za-z0-9_]*\s*=\s*[^=]{1,120}",

        # Big-O and related complexity notation
        r"\bO\s*\([^)]{1,60}\)",
        r"\bΘ\s*\([^)]{1,60}\)",
        r"\bΩ\s*\([^)]{1,60}\)",

        # Mathematical symbols
        r"[≤≥≠∑∏√∞∈⊆∪∩→←±×÷]",

        # Absolute value notation
        r"\|[A-Za-z_][A-Za-z0-9_]*\|",

        # Powers
        r"\b\d+\s*\^\s*\d+\b",

        # Fractions
        r"\b[A-Za-z0-9]+\s*/\s*[A-Za-z0-9]+\b",
    ]

    for line in get_lines(text):

        if is_irrelevant(line):
            continue

        if len(line) > 250 or "?" in line:
            continue

        if re.match(
            r"^(?:example|step|why|what)\b",
            line,
            re.IGNORECASE
        ):
            continue

        if any(re.search(pattern, line) for pattern in patterns):
            formulas.append(line)

    return remove_duplicates(formulas)


# --------------------------------------------------
# ALGORITHMS
# --------------------------------------------------

def extract_algorithms(text):
    """
    Extract algorithm headings, procedure descriptions
    and explicitly labelled steps.
    """

    algorithms = []

    heading_pattern = re.compile(
        r"^(?:algorithm\b|pseudocode\b|procedure\b)",
        re.IGNORECASE
    )

    step_pattern = re.compile(
        r"^(?:step\s*\d+|steps?\s*:|"
        r"\d+[.)]\s+)",
        re.IGNORECASE
    )

    algorithm_keywords = (
        "algorithm",
        "greedy method",
        "dynamic programming",
        "divide and conquer",
        "backtracking",
        "branch and bound",
        "approximation algorithm",
    )

    for line in get_lines(text):

        if is_irrelevant(line):
            continue

        # Explicit algorithm headings
        if heading_pattern.match(line):
            algorithms.append(line)
            continue

        # Explicitly numbered steps
        if step_pattern.match(line) and len(line.split()) >= 4:
            algorithms.append(line)
            continue

        # Sentences describing an algorithm
        lower = line.lower()

        if (
            any(keyword in lower for keyword in algorithm_keywords)
            and len(line.split()) >= 7
            and is_complete_sentence(line)
        ):
            algorithms.append(line)

    return remove_duplicates(algorithms)


# --------------------------------------------------
# IMPORTANT POINTS / QUICK REVISION
# --------------------------------------------------

def extract_important_points(text, limit=15):
    """Extract relevant, complete revision statements."""

    points = []

    keywords = [
        "important",
        "therefore",
        "however",
        "property",
        "characteristic",
        "advantage",
        "disadvantage",
        "complexity",
        "application",
        "key concept",
        "guarantee",
        "polynomial time",
        "exponential time",
        "efficient",
        "intractable",
        "optimal solution",
        "np-complete",
        "np-hard",
        "vertex cover",
        "satisfiability",
        "approximation algorithm",
        "time complexity",
        "space complexity",
        "feasible solution",
        "optimal",
        "reduction",
    ]

    excluded_starts = (
        "example:",
        "for example",
        "for instance",
        "what:",
        "why:",
        "step ",
        "algorithm:",
        "input:",
        "output:",
    )

    for sentence in get_sentences(text):

        lower = sentence.lower().strip()

        if is_irrelevant(sentence):
            continue

        if not is_complete_sentence(sentence):
            continue

        if lower.startswith(excluded_starts):
            continue

        if len(sentence) > 350:
            continue

        score = sum(
            1 for keyword in keywords
            if keyword in lower
        )

        if score > 0:
            points.append((score, sentence))

    # Higher keyword relevance first
    points.sort(key=lambda item: item[0], reverse=True)

    selected = [
        sentence
        for _, sentence in points[:limit]
    ]

    return remove_duplicates(selected)


# --------------------------------------------------
# MAIN CLASSIFIER
# --------------------------------------------------

def classify_document(text):
    """Return structured content extracted from a document."""

    text = clean_text(text)

    return {
        "definitions": extract_definitions(text),
        "examples": extract_examples(text),
        "formulas": extract_formulas(text),
        "algorithms": extract_algorithms(text),
        "important_points": extract_important_points(text),
    }
