"""
Student Feedback Analysis Module (CO2)

Purpose:
    After a BrainCheck quiz, a student can rate the quiz (1-5 stars) and
    write feedback. This module:

      1. Finds the overall sentiment of the feedback (VADER, nlp/sentiment.py).
      2. Finds WHAT the feedback talks about (aspects such as Difficulty or
         Timer) and the sentiment of each aspect: aspect-based sentiment
         analysis, a simple form of information extraction.
      3. Summarises all feedback together with quiz scores, to show how
         students' feelings relate to their performance.
      4. Evaluates VADER on real student feedback, using each student's own
         star rating as the true label:
             4-5 stars -> Positive, 3 stars -> Neutral, 1-2 stars -> Negative.

    No database code here: app.py stores and loads the rows, and this module
    only analyses them, so it can be tested on its own.

CO Mapping: CO2 - Implementation and evaluation of sentiment analysis
            and information extraction using appropriate algorithms.
"""

import re

import numpy as np

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

MIN_FEEDBACK_CHARS = 3
MAX_FEEDBACK_CHARS = 1000

SENTIMENT_LABELS = ["Positive", "Neutral", "Negative"]

# Aspect lexicon: an aspect is mentioned when any of its words appears.
# Words are matched at the START of a word, so "explain" also matches
# "explained" and "explanation".
ASPECT_KEYWORDS = {
    "Difficulty": ["difficult", "hard", "easy", "tough", "simple", "complex",
                   "challeng", "confus", "basic", "advanced", "level"],
    "Timer": ["time", "timer", "fast", "slow", "rush", "minute", "second",
              "quick", "hurry"],
    "Questions": ["question", "mcq", "option", "wording", "tricky",
                  "repeat", "relevant", "ambiguous"],
    "Explanations": ["explain", "explanation", "answer", "review", "reason",
                     "solution"],
    "Topic coverage": ["topic", "syllabus", "coverage", "concept", "cover",
                       "unit", "chapter"],
}


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def rating_to_label(rating):
    """Convert a 1-5 star rating into a sentiment label (or None if no rating)."""

    if rating is None:
        return None
    if rating >= 4:
        return "Positive"
    if rating == 3:
        return "Neutral"
    return "Negative"


def validate_feedback(text, rating):
    """
    Check the feedback before analysing it.

    Returns:
        (clean_text, rating_or_None)
    Raises:
        ValueError with a message the student can act on.
    """

    if not isinstance(text, str) or len(text.strip()) < MIN_FEEDBACK_CHARS:
        raise ValueError("Please write a few words of feedback.")

    text = " ".join(text.split())

    if len(text) > MAX_FEEDBACK_CHARS:
        raise ValueError(f"Feedback must be under {MAX_FEEDBACK_CHARS} characters.")

    if rating in (None, ""):
        return text, None

    if isinstance(rating, bool):
        raise ValueError("Rating must be a whole number from 1 to 5.")

    try:
        rating = int(rating)
    except (TypeError, ValueError):
        raise ValueError("Rating must be a whole number from 1 to 5.")

    if not 1 <= rating <= 5:
        raise ValueError("Rating must be a whole number from 1 to 5.")

    return text, rating


def split_feedback_sentences(text):
    """Split feedback into sentences at . ! ? and at 'but' (a common contrast word)."""

    parts = re.split(r"(?<=[.!?])\s+|\s+but\s+", text, flags=re.IGNORECASE)
    return [part.strip(" .!?") for part in parts if part.strip(" .!?")]


def find_aspects(sentence):
    """Return the aspects whose keywords appear in a sentence."""

    lower = sentence.lower()
    return [
        aspect
        for aspect, words in ASPECT_KEYWORDS.items()
        if any(re.search(r"\b" + re.escape(word), lower) for word in words)
    ]


# --------------------------------------------------
# 1 + 2. ANALYSE ONE FEEDBACK
# --------------------------------------------------

def analyze_feedback(text, rating=None):
    """
    Analyse one piece of student feedback.

    Returns:
        dict with sentiment, compound, scores, aspects (with per-aspect
        sentiment), the rating, the label implied by the rating, and
        whether VADER agrees with that rating.
    """

    from nlp.sentiment import analyze_sentiment, classify_sentiment

    text, rating = validate_feedback(text, rating)
    overall = analyze_sentiment(text)

    # Aspect-based sentiment: score each sentence, then give each aspect the
    # average compound score of the sentences that mention it.
    aspect_scores = {}
    for sentence in split_feedback_sentences(text):
        aspects = find_aspects(sentence)
        if not aspects:
            continue
        compound = analyze_sentiment(sentence)["compound"]
        for aspect in aspects:
            aspect_scores.setdefault(aspect, []).append(compound)

    aspects = [
        {
            "aspect": aspect,
            "compound": round(float(np.mean(scores)), 4),
            "sentiment": classify_sentiment(float(np.mean(scores))),
        }
        for aspect, scores in aspect_scores.items()
    ]

    rating_label = rating_to_label(rating)

    return {
        "feedback_text": text,
        "sentiment": overall["sentiment"],
        "compound": overall["compound"],
        "scores": overall["scores"],
        "aspects": aspects,
        "rating": rating,
        "rating_label": rating_label,
        "agrees_with_rating": (rating_label == overall["sentiment"]) if rating_label else None,
    }


# --------------------------------------------------
# 3 + 4. SUMMARISE ALL FEEDBACK
# --------------------------------------------------

def _average(values):
    return round(float(np.mean(values)), 1) if values else None


def summarize_feedback(rows):
    """
    Summarise saved feedback together with quiz performance.

    Args:
        rows (list of dict): each has sentiment, compound, rating (or None),
            aspects (list of {"aspect", "sentiment", ...}) and score_percentage.

    Returns:
        dict: distribution, average score per sentiment, score-sentiment
        correlation, aspect counts and VADER-vs-rating evaluation.
    """

    from nlp.evaluation import evaluate_classification

    total = len(rows)
    distribution = {label: 0 for label in SENTIMENT_LABELS}
    scores_by_sentiment = {label: [] for label in SENTIMENT_LABELS}

    for row in rows:
        label = row["sentiment"]
        if label in distribution:
            distribution[label] += 1
            scores_by_sentiment[label].append(float(row["score_percentage"]))

    # Does a happier student score higher? Pearson correlation between
    # quiz score and feedback compound score (-1 .. +1).
    correlation = None
    if total >= 3:
        quiz_scores = [float(row["score_percentage"]) for row in rows]
        compounds = [float(row["compound"]) for row in rows]
        if np.std(quiz_scores) > 0 and np.std(compounds) > 0:
            correlation = round(float(np.corrcoef(quiz_scores, compounds)[0, 1]), 3)

    # How often each aspect is mentioned, and how students feel about it.
    aspect_summary = {}
    for row in rows:
        for item in row.get("aspects") or []:
            entry = aspect_summary.setdefault(
                item["aspect"], {"mentions": 0, "Positive": 0, "Neutral": 0, "Negative": 0})
            entry["mentions"] += 1
            entry[item["sentiment"]] += 1

    aspects = sorted(
        ({"aspect": name, **counts} for name, counts in aspect_summary.items()),
        key=lambda item: item["mentions"],
        reverse=True,
    )

    # Evaluation: VADER prediction vs the student's own star rating.
    rated = [row for row in rows if row.get("rating")]
    evaluation = None
    if rated:
        true_labels = [rating_to_label(int(row["rating"])) for row in rated]
        predicted = [row["sentiment"] for row in rated]
        result = evaluate_classification(true_labels, predicted)
        evaluation = {
            "samples": len(rated),
            "accuracy": result["accuracy"],
            "precision": result["precision"],
            "recall": result["recall"],
            "f1_score": result["f1_score"],
            # confusion_matrix() orders labels alphabetically.
            "confusion_matrix_labels": sorted(set(true_labels) | set(predicted)),
            "confusion_matrix": result["confusion_matrix"],
        }

    ratings = [int(row["rating"]) for row in rated]

    return {
        "total_feedback": total,
        "distribution": distribution,
        "distribution_percentage": {
            label: round(100 * count / total, 1) if total else 0.0
            for label, count in distribution.items()
        },
        "average_score_by_sentiment": {
            label: _average(values) for label, values in scores_by_sentiment.items()
        },
        "average_rating": _average(ratings),
        "average_compound": _average([float(row["compound"]) for row in rows]),
        "score_sentiment_correlation": correlation,
        "aspects": aspects,
        "evaluation": evaluation,
    }
