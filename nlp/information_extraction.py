"""
Information Extraction Module (CO2)

Purpose:
    Pull structured facts out of unstructured study notes:
      1. Definitions      - "Deadlock is a situation where ..."
      2. Acronyms         - "Non-deterministic Polynomial (NP)"
                          (Schwartz & Hearst, 2003 matching algorithm)
      3. Key terms        - the most important words/phrases (TF-IDF)
      4. Complexity terms - Big-O style expressions such as O(n log n)
      5. Dates and years  - 12/08/2025, 1971

Technologies:
    - re (regular expressions): rule-based pattern matching.
    - scikit-learn TfidfVectorizer: key-term scoring.

Why rule-based?
    Study notes follow predictable sentence patterns ("X is ...",
    "... is called X", "Long Name (ABBR)"). Rules are fast, need no
    training data, run fully offline, and every result can be
    explained in a viva by pointing at the pattern that matched.

Evaluation:
    evaluate_on_labelled_set() runs the extractor on a small hand-labelled
    set (LABELLED_EXTRACTION_DATA) and reports precision, recall and F1
    using nlp.evaluation.evaluate_extraction.

CO Mapping: CO2 - Implementation and evaluation of sentiment analysis
            and information extraction using appropriate algorithms.
"""

import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

# Longest sentence (in words) we try to read a definition from.
# Very long sentences are usually explanations, not definitions.
MAX_DEFINITION_SENTENCE_WORDS = 45

# A defined term is short: "Deadlock", "Time complexity", "NP-complete problem".
MAX_TERM_WORDS = 6

# Words that can start a sentence but are never the thing being defined.
NOT_A_TERM = {
    "it", "this", "that", "these", "those", "there", "here", "they",
    "he", "she", "we", "you", "i", "which", "what", "who", "where",
    "when", "why", "how", "each", "such", "its", "our", "their",
    "one", "another", "result", "answer", "following",
}


# --------------------------------------------------
# SENTENCE SPLITTING
# --------------------------------------------------

# Words a heading never ends with; a line ending in one is a wrapped sentence.
FUNCTION_WORDS = {
    "a", "an", "the", "of", "and", "or", "to", "in", "on", "by", "for",
    "with", "is", "are", "that", "which", "as", "at", "from", "be",
}


def _starts_new_piece(previous_line, line):
    """
    Decide whether `line` starts a new sentence/heading instead of
    continuing the previous physical line (PDF text breaks lines in the
    middle of sentences).

    New piece when:
      - the line is a bullet or a numbered item, or
      - the previous line already ended a sentence (. ! ? : ;), or
      - the line starts with a capital letter and the previous line looks like
        a heading or label: short (<= 8 words) and not ending in a word
        like "the"/"of", or long but not ending mid-sentence (no comma or
        function word at the end), as slide titles do.
    """

    if re.match(r"^(?:[•\-\*]|\d+[.)]?\s)", line):
        return True

    if previous_line.endswith((".", "!", "?", ":", ";")):
        return True

    if not line[:1].isupper():
        return False

    # Case-sensitive on purpose: a wrapped sentence ends in lowercase "a"/"the",
    # while a capital "A" at a line end is usually a variable ("problem A").
    last_word = previous_line.split()[-1]
    ends_mid_sentence = previous_line.endswith(",") or last_word in FUNCTION_WORDS

    return not ends_mid_sentence


def split_sentences(text):
    """
    Split text into sentences.

    Step 1: rebuild logical lines from the PDF's physical lines
            (join wrapped lines, rejoin words hyphenated at a line end,
            keep slide headings separate).
    Step 2: split each logical line at '.', '!' or '?' followed by a space.
            Decimal numbers like 3.14 are not split because no space follows the dot.
    """

    if not isinstance(text, str):
        return []

    pieces = []
    current = ""
    previous_line = ""

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line:                                   # blank line ends a piece
            if current:
                pieces.append(current)
            current = ""
        elif not current:
            current = line
        elif current.endswith("-") and line[:1].islower():
            current += line                            # "NP-\nhard" -> "NP-hard"
        elif _starts_new_piece(previous_line, line):
            pieces.append(current)
            current = line
        else:
            current += " " + line

        previous_line = line or previous_line

    if current:
        pieces.append(current)

    sentences = []
    for piece in pieces:
        for part in re.split(r"(?<=[.!?])\s+", piece):
            part = re.sub(r"^(?:[•\-\*]|\d+[.)]?)\s+", "", part).strip(" .")
            if len(part) > 3:
                sentences.append(part)

    return sentences


# --------------------------------------------------
# 1. DEFINITIONS
# --------------------------------------------------

# Pattern A: "<Term> is/are/refers to/means <definition>"
DEFINITION_PATTERN = re.compile(
    r"^(?P<term>[A-Za-z][A-Za-z0-9\-\s/()']{0,60}?)\s+"
    r"(?:is defined as|are defined as|refers to|refer to|"
    r"is known as|is called|means|is|are)\s+"
    r"(?P<definition>.{12,})$",
    flags=re.IGNORECASE,
)

# Pattern B: "<definition> is called/known as/termed <Term>"
CALLED_PATTERN = re.compile(
    r"^(?P<definition>.{12,}?)\s+(?:is|are)\s+(?:called|known as|termed)\s+"
    r"(?:an?\s+|the\s+)?(?P<term>[A-Za-z][A-Za-z0-9\-\s]{1,50})$",
    flags=re.IGNORECASE,
)


def _clean_term(term):
    """Tidy a matched term: drop a leading article and surrounding spaces."""

    term = re.sub(r"^(?:the|a|an)\s+", "", term.strip(), flags=re.IGNORECASE)
    return term.strip(" ,:;-")


# Words that show the "term" is really a clause, a list or an instruction,
# not one concept: "problems that are ...", "TSP and the Halting problem are ...",
# "Trying every route is ...", "To prove B is ...".
CLAUSE_WORDS = {
    "that", "which", "who", "whose", "where", "when", "if", "because",
    "and", "or", "to", "every", "all", "some", "any", "most", "many",
}


def _is_valid_term(term):
    """
    A term must be short, must not start with a pronoun or filler word,
    and must be a single concept (no clause words or "and" lists).
    """

    words = term.split()

    if not words or len(words) > MAX_TERM_WORDS:
        return False

    if words[0].lower() in NOT_A_TERM:
        return False

    if any(word.lower() in CLAUSE_WORDS for word in words):
        return False

    # Reject terms that are only numbers or symbols.
    return bool(re.search(r"[A-Za-z]{2,}", term))


def extract_definitions(text, limit=15):
    """
    Find "term -> definition" pairs in the text.

    Returns:
        list of dicts: {"term", "definition", "sentence"}
    """

    definitions = []
    seen_terms = set()

    for sentence in split_sentences(text):

        if len(sentence.split()) > MAX_DEFINITION_SENTENCE_WORDS:
            continue

        match = CALLED_PATTERN.match(sentence) or DEFINITION_PATTERN.match(sentence)

        if not match:
            continue

        term = _clean_term(match.group("term"))
        definition = match.group("definition").strip()

        # A real definition says something: at least 4 words.
        if not _is_valid_term(term) or len(definition.split()) < 4:
            continue

        key = term.lower()

        if key in seen_terms:
            continue

        seen_terms.add(key)
        definitions.append({
            "term": term,
            "definition": definition,
            "sentence": sentence,
        })

        if len(definitions) >= limit:
            break

    return definitions


# --------------------------------------------------
# 2. ACRONYMS
# --------------------------------------------------

def find_long_form(acronym, candidate):
    """
    Schwartz & Hearst (2003) algorithm for matching an acronym to its long form.

    Walk BACKWARDS through the acronym and the candidate text together:
    every letter of the acronym must be found, in order, inside the
    candidate, and the acronym's FIRST letter must start a word.
    This handles "DataBase Management System" -> DBMS, which a plain
    "first letter of each word" rule misses.

    Returns the shortest matching long form, or None.
    """

    short_index = len(acronym) - 1
    long_index = len(candidate) - 1

    while short_index >= 0:
        letter = acronym[short_index].lower()

        if not letter.isalnum():
            short_index -= 1
            continue

        # Move left until the letter matches; for the first acronym letter
        # the match must also be at the start of a word.
        while long_index >= 0 and (
            candidate[long_index].lower() != letter
            or (short_index == 0 and long_index > 0 and candidate[long_index - 1].isalnum())
        ):
            long_index -= 1

        if long_index < 0:
            return None

        long_index -= 1
        short_index -= 1

    # The long form starts at the beginning of the word holding the first match.
    start = candidate.rfind(" ", 0, long_index + 1) + 1
    return candidate[start:].strip()


def extract_acronyms(text):
    """
    Find acronyms written as "Long Form (ABBR)".

    The candidate long form is the words just before the bracket, within
    the same sentence, at most min(len+5, len*2) words (the window used by
    Schwartz & Hearst).

    Returns:
        list of dicts: {"acronym", "expansion"}
    """

    results = []
    seen = set()

    for match in re.finditer(r"\(([A-Z][A-Za-z0-9\-]{1,9})\)", text):

        acronym = match.group(1)

        # Must contain at least two capital letters (rules out "(Fig)").
        if sum(1 for ch in acronym if ch.isupper()) < 2 or acronym in seen:
            continue

        # Text before the bracket, cut at the previous sentence boundary.
        preceding = text[max(0, match.start() - 200):match.start()]
        preceding = re.split(r"[.!?;:\n]", preceding)[-1]

        letters = sum(1 for ch in acronym if ch.isalnum())
        window = min(letters + 5, letters * 2)
        candidate = " ".join(preceding.split()[-window:])

        expansion = find_long_form(acronym, candidate)

        # Reject non-answers: too short, or the acronym repeated.
        if not expansion or len(expansion) <= len(acronym) or acronym in expansion:
            continue

        seen.add(acronym)
        results.append({"acronym": acronym, "expansion": expansion})

    return results


# --------------------------------------------------
# 3. KEY TERMS (TF-IDF)
# --------------------------------------------------

def extract_key_terms(text, top_n=15):
    """
    Score words and two-word phrases with TF-IDF across the
    sentences of the document and return the highest-scoring ones.

    TF-IDF rewards a term that appears often in some sentences
    but not in every sentence, which is what an important,
    topic-specific term looks like.
    """

    sentences = [s for s in split_sentences(text) if len(s.split()) >= 4]

    if len(sentences) < 2:
        return []

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z\-]{2,}\b",   # words of 3+ letters
        sublinear_tf=True,
        max_df=0.8,
    )

    try:
        matrix = vectorizer.fit_transform(sentences)
    except ValueError:
        return []

    # Average weight of each term over all sentences.
    scores = np.asarray(matrix.mean(axis=0)).ravel()
    names = vectorizer.get_feature_names_out()
    order = scores.argsort()[::-1]

    terms = []
    for index in order[:top_n]:
        if scores[index] <= 0:
            break
        terms.append({"term": str(names[index]), "score": round(float(scores[index]), 4)})

    return terms


# --------------------------------------------------
# 4. COMPLEXITY EXPRESSIONS AND 5. DATES
# --------------------------------------------------

def extract_complexity_expressions(text):
    """Big-O / Theta / Omega expressions, e.g. O(n log n), Θ(n^2)."""

    found = re.findall(r"\b[OΘΩθω]\s?\([^()]{1,25}\)", text)
    return sorted({re.sub(r"\s+", " ", item) for item in found})


def extract_dates(text):
    """Numeric dates (12/08/2025, 12-08-25) and 4-digit years (1971, 2024)."""

    dates = re.findall(r"\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b", text)
    years = re.findall(r"\b(?:19|20)\d{2}\b", text)
    return {"dates": sorted(set(dates)), "years": sorted(set(years))}


# --------------------------------------------------
# MAIN ENTRY POINT
# --------------------------------------------------

def extract_information(text, top_terms=15):
    """
    Run every extractor on one document.

    Returns:
        dict with definitions, acronyms, key_terms,
        complexity_expressions, dates, years and counts.
    """

    if not isinstance(text, str) or not text.strip():
        raise ValueError("Please provide text for information extraction.")

    definitions = extract_definitions(text)
    acronyms = extract_acronyms(text)
    key_terms = extract_key_terms(text, top_n=top_terms)
    complexity = extract_complexity_expressions(text)
    dates = extract_dates(text)

    return {
        "definitions": definitions,
        "acronyms": acronyms,
        "key_terms": key_terms,
        "complexity_expressions": complexity,
        "dates": dates["dates"],
        "years": dates["years"],
        "counts": {
            "definitions": len(definitions),
            "acronyms": len(acronyms),
            "key_terms": len(key_terms),
            "complexity_expressions": len(complexity),
        },
    }


# --------------------------------------------------
# EVALUATION ON A HAND-LABELLED SET
# --------------------------------------------------

# Each sample lists what a careful human would extract.
# A few samples are deliberately hard (no definition, pronoun subjects,
# long-form words that don't match the acronym) so the score is honest.
LABELLED_EXTRACTION_DATA = [
    {
        "text": "Deadlock is a situation where two transactions wait for each other forever.",
        "definitions": ["deadlock"],
        "acronyms": [],
    },
    {
        "text": "Time complexity is the amount of time an algorithm takes as a function of input size.",
        "definitions": ["time complexity"],
        "acronyms": [],
    },
    {
        "text": "A problem that can be solved in polynomial time by a deterministic machine is called a tractable problem.",
        "definitions": ["tractable problem"],
        "acronyms": [],
    },
    {
        "text": "Non-deterministic Polynomial (NP) problems can be verified in polynomial time.",
        "definitions": [],
        "acronyms": ["NP=non-deterministic polynomial"],
    },
    {
        "text": "The Travelling Salesman Problem (TSP) asks for the shortest tour visiting every city once.",
        "definitions": [],
        "acronyms": ["TSP=travelling salesman problem"],
    },
    {
        "text": "Database Management System (DBMS) software stores data. Normalization refers to organising tables to reduce redundancy.",
        "definitions": ["normalization"],
        "acronyms": ["DBMS=database management system"],
    },
    {
        "text": "It is important to revise every unit before the exam.",
        "definitions": [],
        "acronyms": [],
    },
    {
        "text": "A greedy algorithm makes the locally best choice at every step.",
        "definitions": ["greedy algorithm"],
        "acronyms": [],
    },
    {
        "text": "Cook's theorem shows that SAT is NP-complete. Boolean satisfiability (SAT) was the first such problem.",
        "definitions": [],
        "acronyms": ["SAT=boolean satisfiability"],
    },
    {
        "text": "We now move to the next topic in the syllabus.",
        "definitions": [],
        "acronyms": [],
    },
    {
        "text": "Dynamic programming solves problems by combining solutions of overlapping subproblems.",
        "definitions": [],          # "solves" is not a definition verb -> correctly nothing
        "acronyms": [],
    },
    {
        "text": "A reduction is a way of converting one problem into another problem.",
        "definitions": ["reduction"],
        "acronyms": [],
    },
]


def predict_labels(text):
    """Run the extractors on one text and return comparable label strings."""

    definitions = [d["term"].lower() for d in extract_definitions(text)]
    acronyms = [
        f"{a['acronym']}={a['expansion'].lower()}"
        for a in extract_acronyms(text)
    ]
    return definitions, acronyms


def evaluate_on_labelled_set(samples=None):
    """
    Measure precision, recall and F1 for definitions and acronyms.

    Every label is prefixed with its sample number, so the same term in
    two samples counts twice (micro-averaged over the whole set).
    """

    from nlp.evaluation import evaluate_extraction

    samples = samples or LABELLED_EXTRACTION_DATA

    true_definitions, predicted_definitions = [], []
    true_acronyms, predicted_acronyms = [], []

    for number, sample in enumerate(samples):
        definitions, acronyms = predict_labels(sample["text"])

        true_definitions += [f"{number}:{label}" for label in sample["definitions"]]
        predicted_definitions += [f"{number}:{label}" for label in definitions]
        true_acronyms += [f"{number}:{label}" for label in sample["acronyms"]]
        predicted_acronyms += [f"{number}:{label}" for label in acronyms]

    return {
        "samples": len(samples),
        "definitions": evaluate_extraction(true_definitions, predicted_definitions),
        "acronyms": evaluate_extraction(true_acronyms, predicted_acronyms),
    }
