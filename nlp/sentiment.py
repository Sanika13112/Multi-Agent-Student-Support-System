
"""
Sentiment Analysis Module (CO2)

Purpose:
    Analyze sentiment of student text, feedback, or document content
    using NLTK VADER (Valence Aware Dictionary and sEntiment Reasoner).

Technologies:
    - NLTK VADER: Rule-based sentiment analysis optimized for social
      media and short text, works well for student feedback.
    - Custom classification: Maps compound scores to sentiment labels.

CO Mapping: CO2 — Implementation and evaluation of sentiment analysis
             and information extraction using appropriate algorithms.
"""

import re
import logging

from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.tokenize import sent_tokenize

logger = logging.getLogger(__name__)

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

# VADER compound score thresholds for classification.
POSITIVE_THRESHOLD = 0.05
NEGATIVE_THRESHOLD = -0.05

# Lazy-loaded VADER analyzer instance.
_vader_analyzer = None


# --------------------------------------------------
# LOAD VADER MODEL
# --------------------------------------------------

def get_vader_analyzer():
    """Load the VADER sentiment analyzer once and reuse it."""

    global _vader_analyzer

    if _vader_analyzer is None:
        try:
            _vader_analyzer = SentimentIntensityAnalyzer()
            logger.info("VADER sentiment analyzer loaded successfully.")
        except LookupError:
            # Download VADER lexicon if not already present.
            import nltk
            nltk.download("vader_lexicon", quiet=True)
            nltk.download("punkt_tab", quiet=True)
            _vader_analyzer = SentimentIntensityAnalyzer()
            logger.info("VADER lexicon downloaded and analyzer loaded.")

    return _vader_analyzer


# --------------------------------------------------
# TEXT PREPROCESSING FOR SENTIMENT
# --------------------------------------------------

def preprocess_for_sentiment(text):
    """
    Lightly preprocess text for sentiment analysis.

    Unlike general NLP preprocessing, sentiment analysis
    preserves punctuation, capitalization cues and emoticons
    because VADER uses them for scoring.
    """

    if not isinstance(text, str):
        return ""

    # Remove null bytes and normalize whitespace.
    text = text.replace("\x00", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# --------------------------------------------------
# CLASSIFY SENTIMENT LABEL
# --------------------------------------------------

def classify_sentiment(compound_score):
    """
    Map a VADER compound score to a human-readable label.

    Args:
        compound_score (float): VADER compound score (-1 to +1).

    Returns:
        str: "Positive", "Negative", or "Neutral".
    """

    if compound_score >= POSITIVE_THRESHOLD:
        return "Positive"
    elif compound_score <= NEGATIVE_THRESHOLD:
        return "Negative"
    else:
        return "Neutral"


# --------------------------------------------------
# ANALYZE SINGLE TEXT
# --------------------------------------------------

def analyze_sentiment(text):
    """
    Perform sentiment analysis on a single text input.

    Uses VADER to compute polarity scores and classify
    the overall sentiment.

    Args:
        text (str): Input text to analyze.

    Returns:
        dict: Sentiment analysis result containing:
            - text: Original input text.
            - scores: VADER polarity scores (pos, neg, neu, compound).
            - sentiment: Classified sentiment label.
            - compound: Compound score for quick access.
    """

    if not isinstance(text, str) or not text.strip():
        raise ValueError("Input text cannot be empty.")

    analyzer = get_vader_analyzer()
    cleaned = preprocess_for_sentiment(text)

    # VADER returns: neg, neu, pos, compound
    scores = analyzer.polarity_scores(cleaned)

    sentiment_label = classify_sentiment(scores["compound"])

    return {
        "text": text.strip(),
        "scores": {
            "positive": round(scores["pos"], 4),
            "negative": round(scores["neg"], 4),
            "neutral": round(scores["neu"], 4),
            "compound": round(scores["compound"], 4),
        },
        "sentiment": sentiment_label,
        "compound": round(scores["compound"], 4),
    }


# --------------------------------------------------
# SENTENCE-LEVEL SENTIMENT ANALYSIS
# --------------------------------------------------

def analyze_sentences(text):
    """
    Perform sentence-level sentiment analysis.

    Splits the text into individual sentences and analyzes
    each sentence separately, providing granular insight.

    Args:
        text (str): Input text with one or more sentences.

    Returns:
        dict: Contains sentence-level results and overall summary.
    """

    if not isinstance(text, str) or not text.strip():
        raise ValueError("Input text cannot be empty.")

    analyzer = get_vader_analyzer()
    cleaned = preprocess_for_sentiment(text)

    try:
        sentences = sent_tokenize(cleaned)
    except LookupError:
        import nltk
        nltk.download("punkt_tab", quiet=True)
        sentences = sent_tokenize(cleaned)

    if not sentences:
        raise ValueError("No sentences could be extracted from the text.")

    sentence_results = []
    compound_scores = []

    for sentence in sentences:
        sentence = sentence.strip()

        if not sentence:
            continue

        scores = analyzer.polarity_scores(sentence)
        compound = scores["compound"]
        compound_scores.append(compound)

        sentence_results.append({
            "sentence": sentence,
            "scores": {
                "positive": round(scores["pos"], 4),
                "negative": round(scores["neg"], 4),
                "neutral": round(scores["neu"], 4),
                "compound": round(compound, 4),
            },
            "sentiment": classify_sentiment(compound),
        })

    # Compute overall statistics.
    total_sentences = len(sentence_results)

    positive_count = sum(
        1 for result in sentence_results
        if result["sentiment"] == "Positive"
    )

    negative_count = sum(
        1 for result in sentence_results
        if result["sentiment"] == "Negative"
    )

    neutral_count = sum(
        1 for result in sentence_results
        if result["sentiment"] == "Neutral"
    )

    average_compound = (
        sum(compound_scores) / len(compound_scores)
        if compound_scores else 0.0
    )

    overall_sentiment = classify_sentiment(average_compound)

    return {
        "total_sentences": total_sentences,
        "overall_sentiment": overall_sentiment,
        "average_compound": round(average_compound, 4),
        "distribution": {
            "positive": positive_count,
            "negative": negative_count,
            "neutral": neutral_count,
        },
        "distribution_percentage": {
            "positive": round(
                positive_count / total_sentences * 100, 2
            ) if total_sentences else 0.0,
            "negative": round(
                negative_count / total_sentences * 100, 2
            ) if total_sentences else 0.0,
            "neutral": round(
                neutral_count / total_sentences * 100, 2
            ) if total_sentences else 0.0,
        },
        "sentences": sentence_results,
    }


# --------------------------------------------------
# BATCH SENTIMENT ANALYSIS
# --------------------------------------------------

def analyze_batch(texts):
    """
    Analyze sentiment for a list of text inputs.

    Useful for analyzing multiple student feedback entries
    or quiz comments at once.

    Args:
        texts (list): List of text strings.

    Returns:
        dict: Batch results with individual and aggregate analysis.
    """

    if not isinstance(texts, list) or not texts:
        raise ValueError("Please provide a non-empty list of texts.")

    results = []

    for text in texts:
        if isinstance(text, str) and text.strip():
            results.append(analyze_sentiment(text))

    if not results:
        raise ValueError("No valid text entries found in the input.")

    compounds = [r["compound"] for r in results]
    average_compound = sum(compounds) / len(compounds)

    positive_count = sum(1 for r in results if r["sentiment"] == "Positive")
    negative_count = sum(1 for r in results if r["sentiment"] == "Negative")
    neutral_count = sum(1 for r in results if r["sentiment"] == "Neutral")

    return {
        "total_analyzed": len(results),
        "overall_sentiment": classify_sentiment(average_compound),
        "average_compound": round(average_compound, 4),
        "distribution": {
            "positive": positive_count,
            "negative": negative_count,
            "neutral": neutral_count,
        },
        "results": results,
    }
