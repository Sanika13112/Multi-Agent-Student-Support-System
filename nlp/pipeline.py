"""
End-to-End NLP Pipeline (CO1 - CO4)

Purpose:
    Run ONE study document through every NLP stage of the project, in order,
    and produce a single report that shows the output of each stage.
    This is what the project demonstration (30 marks) walks through.

        CO1  1. Text extraction          PDF/TXT -> raw text           (pypdf)
             2. Cleaning                 lower-case, remove symbols    (re)
             3. Tokenization + stop words + stemming                  (NLTK)
             4. Vectorization            TF-IDF matrix                 (scikit-learn)
        CO2  5. Sentiment analysis       sentence-level VADER          (NLTK)
             6. Information extraction   definitions, acronyms, terms  (rules + TF-IDF)
             7. Evaluation               accuracy / precision / recall / F1
        CO3  8. Topic modeling           LDA topics + perplexity       (scikit-learn)
             9. Language detection       fastText lid.176              (offline)
        CO4 10. LLM summary              engineered prompt -> Qwen     (Ollama, local)
        CO3 11. Cloud translation        summary -> Hindi / Marathi    (MyMemory API)

    Stage 11 runs last because it translates the LLM summary from stage 10.

Design:
    - Each stage is a small function returning (one-line summary, details).
    - _run_stage() times it and records "done", "skipped" or "failed".
      A failed stage never stops the stages that do not depend on it, and
      nothing is ever replaced with made-up output.

Used by:
    - run_pipeline.py              (command line, writes JSON + Markdown reports)
    - app.py /api/nlp-pipeline/run (the NLP Pipeline page)
"""

import time
from collections import Counter
from datetime import datetime

from nltk.stem import PorterStemmer

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

# Longer documents are cut to this size so every stage stays fast on a laptop.
MAX_ANALYSIS_CHARS = 100_000

# Size of the pieces the document is split into for TF-IDF and LDA.
SEGMENT_CHARS = 500

DEFAULT_NUM_TOPICS = 5

LLM_TEMPERATURE = 0.3        # low = factual and repeatable
LLM_MAX_TOKENS = 450

# ---- Prompt engineering (CO4) ----
# Role + rules go in the system prompt; the task, grounded context and the
# exact output format go in the user prompt.
SYSTEM_PROMPT = """You are StudyMate AI, a careful teaching assistant for engineering students.
Rules:
1. Use ONLY the information inside the CONTEXT section. Do not add outside facts.
2. If the context does not contain something, say "Not covered in the notes".
3. Write in simple English and keep technical terms exactly as written.
4. Follow the OUTPUT FORMAT exactly, including the three headings."""

USER_PROMPT_TEMPLATE = """TASK: Summarise these study notes for exam revision.

CONTEXT
Document: {title}
Key terms found by TF-IDF: {key_terms}
Topics found by LDA: {topics}
Definitions found in the notes:
{definitions}

Notes (extract):
\"\"\"
{excerpt}
\"\"\"

OUTPUT FORMAT
Summary:
<3 sentences>

Key points:
- <point 1>
- <point 2>
- <point 3>
- <point 4>
- <point 5>

Exam question:
<one question a teacher could ask from these notes>"""

LLM_EXCERPT_CHARS = 2500     # keeps the prompt inside the model's 4096-token window
OUTPUT_SECTIONS = ("Summary:", "Key points:", "Exam question:")


class StageSkipped(Exception):
    """Raised inside a stage that has nothing to do (e.g. LLM switched off)."""


_stemmer = PorterStemmer()


# --------------------------------------------------
# STAGE RUNNER
# --------------------------------------------------

def _run_stage(report, number, co, title, method, stage_function):
    """
    Run one stage, time it and append its record to the report.

    Returns the stage's details dict if it finished, otherwise None,
    so later stages can check whether their input exists.
    """

    started = time.perf_counter()

    try:
        summary, details = stage_function()
        status = "done"
    except StageSkipped as reason:
        summary, details, status = str(reason), {}, "skipped"
    except Exception as error:      # record the real error, never fake a result
        summary, details, status = f"{type(error).__name__}: {error}", {}, "failed"

    report["stages"].append({
        "number": number,
        "co": co,
        "title": title,
        "method": method,
        "status": status,
        "seconds": round(time.perf_counter() - started, 3),
        "summary": summary,
        "details": details,
    })

    return details if status == "done" else None


def _needs(value, message):
    """Skip the current stage when an earlier stage did not produce its input."""

    if not value:
        raise StageSkipped(message)
    return value


# --------------------------------------------------
# CO1 STAGES
# --------------------------------------------------

def stage_extract(file_path, text, title):
    """1. Get raw text: from a PDF/TXT file, or use text passed in directly."""

    if file_path:
        from modules.common.document_loader import load_document
        document = load_document(file_path)
        pages = document["pages"]
        raw_text = document["text"]
        source = document["file_type"].upper()
    else:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Provide a PDF/TXT file or some text.")
        raw_text = text.strip()
        pages = [{"page_number": 1, "text": raw_text}]
        source = "pasted text"

    truncated = len(raw_text) > MAX_ANALYSIS_CHARS
    raw_text = raw_text[:MAX_ANALYSIS_CHARS]
    empty_pages = [page["page_number"] for page in pages if not page["text"].strip()]

    details = {
        "source": source,
        "title": title,
        "pages": len(pages),
        "empty_pages": empty_pages,
        "characters": len(raw_text),
        "words": len(raw_text.split()),
        "truncated": truncated,
        "preview": raw_text[:300],
        "text": raw_text,                       # removed before the report is returned
    }
    summary = f"{len(pages)} page(s), {len(raw_text):,} characters, {len(raw_text.split()):,} words"
    if truncated:
        summary += f" (cut to the first {MAX_ANALYSIS_CHARS:,} characters)"
    return summary, details


def stage_clean(raw_text):
    """2. Clean: lower-case, keep letters/digits/spaces, collapse whitespace."""

    from nlp.preprocess import clean_text

    cleaned = clean_text(raw_text)
    removed = len(raw_text) - len(cleaned)

    details = {
        "characters_before": len(raw_text),
        "characters_after": len(cleaned),
        "characters_removed": removed,
        "before_sample": raw_text[:200],
        "after_sample": cleaned[:200],
        "cleaned_text": cleaned,                # removed before the report is returned
    }
    return f"{removed:,} characters of symbols/extra spaces removed", details


def stage_tokenize(cleaned_text):
    """
    3. Tokenize, remove stop words (keeping negations/question words),
       drop 1-character tokens, then stem.

    Single characters mostly come from letter-spaced slide headings
    ("D E S I G N") and carry no meaning; TF-IDF in stage 4 ignores them too.
    """

    from nlp.preprocess import remove_stopwords, tokenize_text

    tokens = tokenize_text(cleaned_text)
    without_stopwords = remove_stopwords(tokens)
    content_tokens = [token for token in without_stopwords if len(token) > 1]
    stems = [_stemmer.stem(token) for token in content_tokens]
    frequent = Counter(stems).most_common(12)

    details = {
        "tokens": len(tokens),
        "after_stopword_removal": len(without_stopwords),
        "stopwords_removed": len(tokens) - len(without_stopwords),
        "single_characters_removed": len(without_stopwords) - len(content_tokens),
        "content_tokens": len(content_tokens),
        "unique_tokens": len(set(content_tokens)),
        "unique_stems": len(set(stems)),
        "sample_tokens": content_tokens[:20],
        "sample_stems": [
            {"token": token, "stem": stem}
            for token, stem in list(zip(content_tokens, stems))[:12]
        ],
        "most_frequent_stems": [{"stem": stem, "count": count} for stem, count in frequent],
    }
    summary = (f"{len(tokens):,} tokens -> {len(without_stopwords):,} after stop-word removal "
               f"-> {len(content_tokens):,} after dropping 1-letter tokens -> {len(set(stems)):,} unique stems")
    return summary, details


def stage_vectorize(raw_text):
    """4. TF-IDF: split into ~500-character segments, one vector per segment."""

    from nlp.preprocess import vectorize_text
    from nlp.topic_modeling import split_into_segments

    segments = split_into_segments(raw_text, segment_size=SEGMENT_CHARS) or [raw_text]
    result = vectorize_text(segments)
    matrix = result["vectors"]
    rows, columns = matrix.shape

    # Sparsity: share of the matrix that is zero (most words are absent from a segment).
    sparsity = 100 * (1 - matrix.nnz / max(rows * columns, 1))

    mean_weights = matrix.mean(axis=0).A1
    names = result["feature_names"]
    top = mean_weights.argsort()[::-1][:12]

    details = {
        "segments": rows,
        "vocabulary_size": columns,
        "matrix_shape": [rows, columns],
        "non_zero_values": int(matrix.nnz),
        "sparsity_percent": round(sparsity, 2),
        "ngram_range": "1-2 (single words and word pairs)",
        "top_terms": [
            {"term": names[index], "mean_tfidf": round(float(mean_weights[index]), 4)}
            for index in top
        ],
    }
    summary = f"TF-IDF matrix {rows} segments x {columns:,} terms, {sparsity:.1f}% sparse"
    return summary, details


# --------------------------------------------------
# CO2 STAGES
# --------------------------------------------------

def stage_sentiment(raw_text):
    """
    5. Sentence-level sentiment with VADER.

    Slides and PDFs often have no full stops, so NLTK's sentence splitter
    would merge whole slides into one "sentence". We first use the same
    line-aware splitter as information extraction, drop 1-3 word headings,
    and end each sentence with a full stop before VADER sees it.
    """

    from nlp.information_extraction import split_sentences
    from nlp.sentiment import analyze_sentences

    sentences = [s for s in split_sentences(raw_text) if len(s.split()) >= 4]
    _needs(sentences, "No full sentences (4+ words) found for sentiment analysis.")
    prepared = " ".join(s if s.endswith(("?", "!")) else s + "." for s in sentences)

    result = analyze_sentences(prepared)
    sentences = result["sentences"]
    ranked = sorted(sentences, key=lambda s: s["scores"]["compound"])

    details = {
        "overall_sentiment": result["overall_sentiment"],
        "average_compound": result["average_compound"],
        "total_sentences": result["total_sentences"],
        "distribution": result["distribution"],
        "distribution_percentage": result["distribution_percentage"],
        "most_negative": ranked[0] if ranked else None,
        "most_positive": ranked[-1] if ranked else None,
        "note": "Study notes are mostly factual, so a high Neutral share is expected.",
    }
    pct = result["distribution_percentage"]
    summary = (f"{result['overall_sentiment']} overall (compound {result['average_compound']}); "
               f"{pct['positive']}% positive, {pct['neutral']}% neutral, {pct['negative']}% negative")
    return summary, details


def stage_extract_information(raw_text):
    """6. Rule-based information extraction."""

    from nlp.information_extraction import extract_information

    info = extract_information(raw_text)
    counts = info["counts"]
    summary = (f"{counts['definitions']} definitions, {counts['acronyms']} acronyms, "
               f"{counts['key_terms']} key terms, {counts['complexity_expressions']} complexity expressions")
    return summary, info


def stage_evaluate():
    """7. Evaluate sentiment and extraction against hand-labelled data."""

    from nlp.evaluation import run_default_evaluation
    from nlp.information_extraction import evaluate_on_labelled_set

    sentiment = run_default_evaluation()
    extraction = evaluate_on_labelled_set()

    def metrics(result):
        return {key: result[key] for key in ("precision", "recall", "f1_score")}

    details = {
        "sentiment": {
            "test_samples": sentiment["total_samples"],
            "accuracy": sentiment["accuracy"],
            "precision": sentiment["precision"],
            "recall": sentiment["recall"],
            "f1_score": sentiment["f1_score"],
            # confusion_matrix() orders labels alphabetically.
            "confusion_matrix_labels": sorted({"Positive", "Negative", "Neutral"}),
            "confusion_matrix": sentiment["confusion_matrix"],
            "wrong_predictions": [
                item for item in sentiment["sentiment_evaluation"]["details"] if not item["correct"]
            ],
        },
        "extraction": {
            "test_samples": extraction["samples"],
            "definitions": metrics(extraction["definitions"]),
            "acronyms": metrics(extraction["acronyms"]),
        },
    }
    summary = (f"Sentiment accuracy {sentiment['accuracy']:.2f} (F1 {sentiment['f1_score']:.2f}) on "
               f"{sentiment['total_samples']} labelled sentences; extraction F1 "
               f"{extraction['definitions']['f1_score']:.2f} (definitions), "
               f"{extraction['acronyms']['f1_score']:.2f} (acronyms)")
    return summary, details


# --------------------------------------------------
# CO3 STAGES
# --------------------------------------------------

def stage_topics(raw_text, num_topics):
    """8. LDA topic modeling."""

    from nlp.topic_modeling import extract_topics_from_text

    result = extract_topics_from_text(raw_text, num_topics=num_topics, segment_size=SEGMENT_CHARS)
    topics = [
        {"topic": topic["topic_id"], "top_words": topic["top_words"][:8]}
        for topic in result["topics"]
    ]
    shares = Counter(doc["dominant_topic"] for doc in result["document_topics"])

    details = {
        "num_topics": result["num_topics"],
        "segments": result["num_documents"],
        "vocabulary_size": result["vocabulary_size"],
        "perplexity": result["model_metrics"]["perplexity"],
        "log_likelihood": result["model_metrics"]["log_likelihood"],
        "topics": topics,
        "segments_per_topic": {str(topic): shares.get(topic, 0) for topic in range(1, result["num_topics"] + 1)},
    }
    summary = f"{result['num_topics']} topics, perplexity {result['model_metrics']['perplexity']:.1f}; " + \
        " | ".join(", ".join(topic["top_words"][:3]) for topic in topics)
    return summary, details


def stage_language(raw_text):
    """9. Language identification."""

    from nlp.multilingual import detect_language

    result = detect_language(raw_text)
    summary = f"{result['name']} (confidence {result['confidence']:.2f}, {result['method']})"
    return summary, result


# --------------------------------------------------
# CO4 STAGE
# --------------------------------------------------

def build_prompt(title, notes_text, information, topics):
    """Fill the prompt template with what the earlier stages found."""

    key_terms = ", ".join(term["term"] for term in (information or {}).get("key_terms", [])[:10]) or "none found"
    topic_text = "; ".join(
        f"Topic {topic['topic']}: {', '.join(topic['top_words'][:5])}" for topic in (topics or {}).get("topics", [])
    ) or "none found"
    definitions = "\n".join(
        f"- {item['term']}: {item['definition']}" for item in (information or {}).get("definitions", [])[:6]
    ) or "- none found"

    return USER_PROMPT_TEMPLATE.format(
        title=title,
        key_terms=key_terms,
        topics=topic_text,
        definitions=definitions,
        excerpt=notes_text[:LLM_EXCERPT_CHARS],
    )


def check_llm_output(output, information):
    """
    Simple automatic checks on the generated text (GenAI evaluation):
      - format: did the model produce all three requested headings?
      - grounding: how many of the document's top key terms does it use?
    """

    lower = output.lower()
    sections = {section.rstrip(":"): section.lower() in lower for section in OUTPUT_SECTIONS}
    key_terms = [term["term"] for term in (information or {}).get("key_terms", [])[:10]]
    used = [term for term in key_terms if term.lower() in lower]

    return {
        "format_followed": all(sections.values()),
        "sections_present": sections,
        "key_terms_checked": len(key_terms),
        "key_terms_used": used,
        "grounding_percent": round(100 * len(used) / len(key_terms), 1) if key_terms else None,
    }


def stage_llm(use_llm, title, raw_text, information, topics):
    """10. Generate a grounded revision summary with the local LLM."""

    if not use_llm:
        raise StageSkipped("LLM step switched off for this run.")

    from modules.common.ai_client import MODEL_NAME, generate_response

    prompt = build_prompt(title, raw_text, information, topics)
    output = generate_response(
        prompt,
        system_prompt=SYSTEM_PROMPT,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
    )
    checks = check_llm_output(output, information)

    details = {
        "model": MODEL_NAME,
        "temperature": LLM_TEMPERATURE,
        "max_tokens": LLM_MAX_TOKENS,
        "prompt_techniques": [
            "Role prompting (system prompt sets the assistant's role)",
            "Grounding: answer only from the CONTEXT section",
            "Context built from earlier pipeline stages (TF-IDF terms, LDA topics, extracted definitions)",
            "Explicit output format with fixed headings",
            "Low temperature for factual, repeatable answers",
        ],
        "system_prompt": SYSTEM_PROMPT,
        "user_prompt": prompt,
        "output": output,
        "checks": checks,
    }
    grounding = checks["grounding_percent"]
    summary = (f"{len(output.split())} words from {MODEL_NAME}; format "
               f"{'followed' if checks['format_followed'] else 'NOT fully followed'}; "
               f"{len(checks['key_terms_used'])}/{checks['key_terms_checked']} key terms used"
               + (f" ({grounding}%)" if grounding is not None else ""))
    return summary, details


# --------------------------------------------------
# CO3 CLOUD STAGE
# --------------------------------------------------

def stage_translate(translate_to, llm, information):
    """11. Translate the LLM summary (or the extracted definitions) with MyMemory."""

    if not translate_to:
        raise StageSkipped("No translation language chosen for this run.")

    from nlp.multilingual import translate

    if llm and llm.get("output"):
        source, source_name = llm["output"], "LLM summary"
    else:
        definitions = (information or {}).get("definitions", [])
        source = " ".join(f"{d['term']}: {d['definition']}." for d in definitions[:4])
        source_name = "extracted definitions"
        _needs(source, "Nothing to translate: no LLM summary and no definitions were extracted.")

    result = translate(source, translate_to)
    result["translated_from"] = source_name
    summary = f"{source_name} translated to {result['target_language_name']} via MyMemory"
    return summary, result


# --------------------------------------------------
# MAIN ENTRY POINT
# --------------------------------------------------

def run_pipeline(file_path=None, text=None, title=None, use_llm=True,
                 translate_to=None, num_topics=DEFAULT_NUM_TOPICS):
    """
    Run all stages on one document and return the report.

    Args:
        file_path (str): PDF or TXT file (or pass `text` instead).
        text (str): raw text, used when no file is given.
        title (str): name shown in the report (defaults to the file name).
        use_llm (bool): run stage 10 (needs Ollama running).
        translate_to (str): "hi" or "mr" to run stage 11 (needs internet), or None.
        num_topics (int): number of LDA topics.

    Returns:
        dict: {"title", "generated_at", "settings", "stages": [...], "totals": {...}}
    """

    from pathlib import Path

    title = title or (Path(file_path).name if file_path else "Pasted text")
    report = {
        "title": title,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "settings": {
            "use_llm": bool(use_llm),
            "translate_to": translate_to or None,
            "num_topics": num_topics,
            "max_analysis_chars": MAX_ANALYSIS_CHARS,
        },
        "stages": [],
    }
    started = time.perf_counter()

    # ---- CO1 ----
    extracted = _run_stage(report, 1, "CO1", "Text extraction", "pypdf / UTF-8 text reader",
                           lambda: stage_extract(file_path, text, title))
    raw = (extracted or {}).get("text", "")

    cleaned = _run_stage(report, 2, "CO1", "Cleaning", "Regular expressions",
                         lambda: stage_clean(_needs(raw, "No text was extracted.")))
    clean_text = (cleaned or {}).get("cleaned_text", "")

    _run_stage(report, 3, "CO1", "Tokenization, stop words and stemming",
               "NLTK word_tokenize + stop-word list + Porter stemmer",
               lambda: stage_tokenize(_needs(clean_text, "No cleaned text available.")))

    _run_stage(report, 4, "CO1", "TF-IDF vectorization", "scikit-learn TfidfVectorizer (1-2 grams)",
               lambda: stage_vectorize(_needs(raw, "No text was extracted.")))

    # ---- CO2 ----
    _run_stage(report, 5, "CO2", "Sentiment analysis", "NLTK VADER, sentence level",
               lambda: stage_sentiment(_needs(raw, "No text was extracted.")))

    information = _run_stage(report, 6, "CO2", "Information extraction",
                             "Rule-based patterns, Schwartz-Hearst acronyms, TF-IDF key terms",
                             lambda: stage_extract_information(_needs(raw, "No text was extracted.")))

    _run_stage(report, 7, "CO2", "Evaluation", "Accuracy, precision, recall, F1, confusion matrix",
               stage_evaluate)

    # ---- CO3 ----
    topics = _run_stage(report, 8, "CO3", "Topic modeling", "Latent Dirichlet Allocation (LDA)",
                        lambda: stage_topics(_needs(raw, "No text was extracted."), num_topics))

    _run_stage(report, 9, "CO3", "Language detection", "fastText lid.176 language identification",
               lambda: stage_language(_needs(raw, "No text was extracted.")))

    # ---- CO4 ----
    llm = _run_stage(report, 10, "CO4", "LLM summary with prompt engineering", "Local Qwen via Ollama",
                     lambda: stage_llm(use_llm, title, _needs(raw, "No text was extracted."),
                                       information, topics))

    # ---- CO3 (cloud, uses the CO4 output) ----
    _run_stage(report, 11, "CO3", "Cloud translation", "MyMemory Translation API",
               lambda: stage_translate(translate_to, llm, information))

    # Large intermediate texts are kept out of the report (the previews remain).
    for stage in report["stages"]:
        stage["details"].pop("text", None)
        stage["details"].pop("cleaned_text", None)

    statuses = Counter(stage["status"] for stage in report["stages"])
    report["totals"] = {
        "stages": len(report["stages"]),
        "done": statuses.get("done", 0),
        "skipped": statuses.get("skipped", 0),
        "failed": statuses.get("failed", 0),
        "seconds": round(time.perf_counter() - started, 2),
    }
    return report


# --------------------------------------------------
# MARKDOWN REPORT
# --------------------------------------------------

def render_markdown(report):
    """Turn a pipeline report into a readable Markdown document for submission."""

    totals = report["totals"]
    lines = [
        f"# NLP Pipeline Report: {report['title']}",
        "",
        f"Generated {report['generated_at']} · {totals['done']}/{totals['stages']} stages done, "
        f"{totals['skipped']} skipped, {totals['failed']} failed · {totals['seconds']} s",
        "",
        "| # | CO | Stage | Method | Status | Time (s) | Result |",
        "|---|---|---|---|---|---|---|",
    ]
    for stage in report["stages"]:
        result = stage["summary"].replace("|", "/")
        lines.append(f"| {stage['number']} | {stage['co']} | {stage['title']} | {stage['method']} | "
                     f"{stage['status']} | {stage['seconds']} | {result} |")

    by_number = {stage["number"]: stage for stage in report["stages"]}

    def done(number):
        stage = by_number.get(number)
        return stage["details"] if stage and stage["status"] == "done" else None

    if done(4):
        lines += ["", "## CO1 · Top TF-IDF terms", ""]
        lines += [f"- {t['term']} ({t['mean_tfidf']})" for t in done(4)["top_terms"]]

    if done(6):
        info = done(6)
        lines += ["", "## CO2 · Extracted information", "", "**Definitions**", ""]
        lines += [f"- **{d['term']}**: {d['definition']}" for d in info["definitions"]] or ["- none found"]
        lines += ["", "**Acronyms**", ""]
        lines += [f"- {a['acronym']} = {a['expansion']}" for a in info["acronyms"]] or ["- none found"]
        lines += ["", "**Complexity expressions:** " + (", ".join(info["complexity_expressions"]) or "none")]

    if done(7):
        evaluation = done(7)
        sentiment, extraction = evaluation["sentiment"], evaluation["extraction"]
        lines += [
            "", "## CO2 · Evaluation", "",
            "| Model | Test samples | Precision | Recall | F1 | Accuracy |",
            "|---|---|---|---|---|---|",
            f"| Sentiment (VADER) | {sentiment['test_samples']} | {sentiment['precision']} | "
            f"{sentiment['recall']} | {sentiment['f1_score']} | {sentiment['accuracy']} |",
            f"| Definition extraction | {extraction['test_samples']} | {extraction['definitions']['precision']} | "
            f"{extraction['definitions']['recall']} | {extraction['definitions']['f1_score']} | – |",
            f"| Acronym extraction | {extraction['test_samples']} | {extraction['acronyms']['precision']} | "
            f"{extraction['acronyms']['recall']} | {extraction['acronyms']['f1_score']} | – |",
        ]

    if done(8):
        lines += ["", "## CO3 · LDA topics", ""]
        lines += [f"- Topic {t['topic']}: {', '.join(t['top_words'])}" for t in done(8)["topics"]]

    if done(10):
        llm = done(10)
        lines += ["", "## CO4 · LLM output", "", f"Model: {llm['model']} · temperature {llm['temperature']}",
                  "", "```text", llm["output"], "```", "",
                  "<details><summary>Prompt used</summary>", "", "```text", llm["user_prompt"], "```",
                  "", "</details>"]

    if done(11):
        lines += ["", f"## CO3 · Translation ({done(11)['target_language_name']})", "",
                  done(11)["translated_text"]]

    return "\n".join(lines) + "\n"
