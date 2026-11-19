
"""
NLP Evaluation Metrics Module (CO2)

Purpose:
    Provide evaluation functions for assessing the performance
    of NLP algorithms used in the project (sentiment analysis,
    information extraction, intent classification).

Technologies:
    - scikit-learn: Provides standard ML evaluation metrics.
    - NumPy: Numerical support for metric computation.

CO Mapping: CO2 — Implementation and evaluation of sentiment analysis
             and information extraction using appropriate algorithms.
"""

import logging

import numpy as np

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------
# CLASSIFICATION EVALUATION
# --------------------------------------------------

def evaluate_classification(
    true_labels,
    predicted_labels,
    label_names=None
):
    """
    Evaluate a classification model using standard metrics.

    Computes accuracy, precision, recall, F1-score, and
    confusion matrix for the given predictions.

    Args:
        true_labels (list): Ground-truth labels.
        predicted_labels (list): Model-predicted labels.
        label_names (list): Optional human-readable label names.

    Returns:
        dict: Evaluation results including all metrics.
    """

    if not isinstance(true_labels, (list, np.ndarray)):
        raise TypeError("true_labels must be a list or numpy array.")

    if not isinstance(predicted_labels, (list, np.ndarray)):
        raise TypeError("predicted_labels must be a list or numpy array.")

    if len(true_labels) != len(predicted_labels):
        raise ValueError(
            "true_labels and predicted_labels must have the same length."
        )

    if len(true_labels) == 0:
        raise ValueError("Cannot evaluate empty label lists.")

    # -----------------------------------------
    # STEP 1: Compute core metrics
    # -----------------------------------------

    accuracy = accuracy_score(true_labels, predicted_labels)

    precision = precision_score(
        true_labels,
        predicted_labels,
        average="weighted",
        zero_division=0,
    )

    recall = recall_score(
        true_labels,
        predicted_labels,
        average="weighted",
        zero_division=0,
    )

    f1 = f1_score(
        true_labels,
        predicted_labels,
        average="weighted",
        zero_division=0,
    )

    # -----------------------------------------
    # STEP 2: Confusion matrix
    # -----------------------------------------

    conf_matrix = confusion_matrix(
        true_labels,
        predicted_labels,
    )

    # -----------------------------------------
    # STEP 3: Per-class metrics
    # -----------------------------------------

    report = classification_report(
        true_labels,
        predicted_labels,
        target_names=label_names,
        zero_division=0,
        output_dict=True,
    )

    # Remove aggregate rows from per-class breakdown.
    per_class = {
        label: metrics
        for label, metrics in report.items()
        if label not in (
            "accuracy", "macro avg", "weighted avg"
        )
    }

    # -----------------------------------------
    # STEP 4: Build results
    # -----------------------------------------

    results = {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "total_samples": len(true_labels),
        "confusion_matrix": conf_matrix.tolist(),
        "per_class_metrics": per_class,
        "classification_report": classification_report(
            true_labels,
            predicted_labels,
            target_names=label_names,
            zero_division=0,
        ),
    }

    logger.info(
        "Evaluation complete | Accuracy: %.4f | F1: %.4f",
        accuracy,
        f1,
    )

    return results


# --------------------------------------------------
# SENTIMENT ANALYSIS EVALUATION
# --------------------------------------------------

def evaluate_sentiment_model(test_data):
    """
    Evaluate the sentiment analysis model against labelled test data.

    Uses the project's own sentiment analyzer to predict labels
    for the test samples, then computes evaluation metrics.

    Args:
        test_data (list): List of dicts with "text" and "expected"
                          keys. Expected values: "Positive",
                          "Negative", or "Neutral".

    Returns:
        dict: Evaluation results for the sentiment model.
    """

    if not isinstance(test_data, list) or not test_data:
        raise ValueError("test_data must be a non-empty list.")

    # Import sentiment module from the same package.
    from nlp.sentiment import analyze_sentiment

    true_labels = []
    predicted_labels = []
    details = []

    for entry in test_data:
        if not isinstance(entry, dict):
            continue

        text = entry.get("text", "")
        expected = entry.get("expected", "")

        if not text or not expected:
            continue

        try:
            result = analyze_sentiment(text)
            predicted = result["sentiment"]

            true_labels.append(expected)
            predicted_labels.append(predicted)

            details.append({
                "text": text[:100],
                "expected": expected,
                "predicted": predicted,
                "compound": result["compound"],
                "correct": expected == predicted,
            })

        except Exception as error:
            logger.warning(
                "Sentiment analysis failed for sample: %s", error
            )

    if not true_labels:
        raise ValueError(
            "No valid test samples could be processed."
        )

    label_names = ["Positive", "Negative", "Neutral"]

    metrics = evaluate_classification(
        true_labels,
        predicted_labels,
        label_names=label_names,
    )

    correct_count = sum(
        1 for detail in details if detail["correct"]
    )

    metrics["sentiment_evaluation"] = {
        "total_samples": len(details),
        "correct_predictions": correct_count,
        "incorrect_predictions": len(details) - correct_count,
        "details": details,
    }

    return metrics


# --------------------------------------------------
# INFORMATION EXTRACTION EVALUATION
# --------------------------------------------------

def evaluate_extraction(
    true_entities,
    predicted_entities,
):
    """
    Evaluate information extraction using set-based
    precision, recall, and F1-score.

    Args:
        true_entities (list): Ground-truth extracted items.
        predicted_entities (list): Model-extracted items.

    Returns:
        dict: Extraction evaluation metrics.
    """

    true_set = set(true_entities)
    predicted_set = set(predicted_entities)

    true_positives = len(true_set & predicted_set)
    false_positives = len(predicted_set - true_set)
    false_negatives = len(true_set - predicted_set)

    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives) > 0
        else 0.0
    )

    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives) > 0
        else 0.0
    )

    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "true_entities": sorted(true_set),
        "predicted_entities": sorted(predicted_set),
        "matched": sorted(true_set & predicted_set),
        "missed": sorted(true_set - predicted_set),
        "extra": sorted(predicted_set - true_set),
    }


# --------------------------------------------------
# BUILT-IN SENTIMENT TEST DATA
# --------------------------------------------------

DEFAULT_SENTIMENT_TEST_DATA = [
    {"text": "This lecture was amazing and very helpful!", "expected": "Positive"},
    {"text": "I really enjoyed learning about neural networks today.", "expected": "Positive"},
    {"text": "The professor explained everything so clearly.", "expected": "Positive"},
    {"text": "Great course material and well-organized notes.", "expected": "Positive"},
    {"text": "I love how easy this tool makes studying.", "expected": "Positive"},
    {"text": "Excellent explanation of algorithms.", "expected": "Positive"},
    {"text": "The best study resource I have found.", "expected": "Positive"},
    {"text": "Very useful and informative session.", "expected": "Positive"},
    {"text": "This topic is so boring and confusing.", "expected": "Negative"},
    {"text": "I did not understand anything from the lecture.", "expected": "Negative"},
    {"text": "The notes were terrible and had many errors.", "expected": "Negative"},
    {"text": "Very frustrating experience with this module.", "expected": "Negative"},
    {"text": "The quiz was unfair and poorly designed.", "expected": "Negative"},
    {"text": "Worst explanation I have ever seen.", "expected": "Negative"},
    {"text": "Completely useless and waste of time.", "expected": "Negative"},
    {"text": "Disappointing quality of study material.", "expected": "Negative"},
    {"text": "The class starts at 10 AM tomorrow.", "expected": "Neutral"},
    {"text": "The exam will cover chapters 3 through 7.", "expected": "Neutral"},
    {"text": "Please submit your assignment by Friday.", "expected": "Neutral"},
    {"text": "The lab session is in Room 204.", "expected": "Neutral"},
    {"text": "Today's lecture covered data structures.", "expected": "Neutral"},
    {"text": "The syllabus includes five units.", "expected": "Neutral"},
    {"text": "Assignment deadline is next Monday.", "expected": "Neutral"},
    {"text": "The midterm exam has 50 marks.", "expected": "Neutral"},
]


def run_default_evaluation():
    """
    Run the sentiment evaluation using the built-in test data.

    Returns:
        dict: Evaluation results using DEFAULT_SENTIMENT_TEST_DATA.
    """

    return evaluate_sentiment_model(DEFAULT_SENTIMENT_TEST_DATA)
