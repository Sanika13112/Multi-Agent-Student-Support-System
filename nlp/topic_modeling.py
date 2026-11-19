
"""
Topic Modeling Module (CO3)

Purpose:
    Discover latent topics in student documents using
    Latent Dirichlet Allocation (LDA).

Technologies:
    - scikit-learn CountVectorizer: Converts text into
      bag-of-words representation for LDA.
    - scikit-learn LatentDirichletAllocation: Probabilistic
      topic modeling algorithm.
    - scikit-learn TfidfVectorizer: TF-IDF for topic keyword
      weighting and document representation.

CO Mapping: CO3 — Implementation of topic modeling or multilingual
             NLP using appropriate NLP techniques and cloud-based
             AI services.
"""

import re
import logging

import numpy as np

from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import (
    CountVectorizer,
    TfidfVectorizer,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

DEFAULT_NUM_TOPICS = 5
DEFAULT_TOP_WORDS = 10
MAX_FEATURES = 5000
MIN_DOCUMENT_FREQUENCY = 2
MAX_DOCUMENT_FREQUENCY_RATIO = 0.90
LDA_MAX_ITERATIONS = 20
LDA_RANDOM_STATE = 42

# Stop words for academic documents.
ACADEMIC_STOP_WORDS = [
    "also", "however", "therefore", "thus", "hence",
    "example", "given", "using", "used", "use",
    "following", "figure", "table", "chapter", "unit",
    "page", "section", "note", "notes", "lecture",
    "assignment", "marks", "total", "answer", "question",
    "student", "students", "professor", "sir", "madam",
    "university", "college", "department", "semester",
    "exam", "examination", "paper", "subject",
]


# --------------------------------------------------
# TEXT PREPROCESSING FOR TOPIC MODELING
# --------------------------------------------------

def preprocess_for_topics(text):
    """
    Prepare text for topic modeling.

    Converts to lowercase, removes special characters,
    and normalizes whitespace while preserving meaningful
    technical terms.

    Args:
        text (str): Raw input text.

    Returns:
        str: Cleaned text suitable for topic modeling.
    """

    if not isinstance(text, str):
        return ""

    text = text.lower()

    # Remove URLs.
    text = re.sub(r"https?://\S+", " ", text)

    # Remove email addresses.
    text = re.sub(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        " ",
        text,
    )

    # Keep only letters and spaces.
    text = re.sub(r"[^a-z\s]", " ", text)

    # Normalize whitespace.
    text = re.sub(r"\s+", " ", text).strip()

    return text


def split_into_segments(text, segment_size=500):
    """
    Split a long document into smaller segments for
    topic modeling when only a single document is provided.

    Args:
        text (str): Full document text.
        segment_size (int): Approximate characters per segment.

    Returns:
        list: List of text segments.
    """

    if not text or not text.strip():
        return []

    words = text.split()
    segments = []
    current_segment = []
    current_length = 0

    for word in words:
        current_segment.append(word)
        current_length += len(word) + 1

        if current_length >= segment_size:
            segments.append(" ".join(current_segment))
            current_segment = []
            current_length = 0

    if current_segment:
        segments.append(" ".join(current_segment))

    # Ensure we have enough segments for meaningful topics.
    if len(segments) < 3:
        # Fall back to sentence-based splitting.
        sentences = re.split(r"[.!?]+\s+", text)
        if len(sentences) >= 3:
            return [s.strip() for s in sentences if s.strip()]

    return segments


# --------------------------------------------------
# TOPIC MODELING WITH LDA
# --------------------------------------------------

def extract_topics(
    documents,
    num_topics=DEFAULT_NUM_TOPICS,
    top_words=DEFAULT_TOP_WORDS,
):
    """
    Extract topics from a collection of documents using LDA.

    Uses CountVectorizer for bag-of-words representation
    and LatentDirichletAllocation for topic discovery.

    Args:
        documents (list): List of text strings (documents or
                          segments of a single document).
        num_topics (int): Number of topics to extract.
        top_words (int): Number of top words per topic.

    Returns:
        dict: Topic modeling results including topics,
              keywords, and document-topic distributions.
    """

    if not isinstance(documents, list) or not documents:
        raise ValueError("Please provide a non-empty list of documents.")

    # Clean documents.
    cleaned_documents = [
        preprocess_for_topics(doc)
        for doc in documents
        if isinstance(doc, str) and doc.strip()
    ]

    if len(cleaned_documents) < 2:
        raise ValueError(
            "At least 2 text segments are needed for topic modeling."
        )

    # Adjust number of topics based on document count.
    num_topics = min(num_topics, len(cleaned_documents))

    if num_topics < 2:
        num_topics = 2

    # -----------------------------------------
    # STEP 1: Create bag-of-words representation
    # -----------------------------------------

    # Determine min_df based on document count.
    min_df = min(MIN_DOCUMENT_FREQUENCY, max(1, len(cleaned_documents) // 3))

    count_vectorizer = CountVectorizer(
        max_features=MAX_FEATURES,
        min_df=min_df,
        max_df=MAX_DOCUMENT_FREQUENCY_RATIO,
        stop_words="english",
        token_pattern=r"\b[a-z]{3,}\b",
    )

    try:
        document_term_matrix = count_vectorizer.fit_transform(
            cleaned_documents
        )
    except ValueError as error:
        raise ValueError(
            "Could not create document-term matrix. "
            "The text may be too short or lack enough unique words."
        ) from error

    feature_names = count_vectorizer.get_feature_names_out()

    if len(feature_names) < num_topics:
        raise ValueError(
            f"Only {len(feature_names)} unique words found. "
            "Need more text content for meaningful topic modeling."
        )

    # -----------------------------------------
    # STEP 2: Train LDA model
    # -----------------------------------------

    lda_model = LatentDirichletAllocation(
        n_components=num_topics,
        max_iter=LDA_MAX_ITERATIONS,
        learning_method="online",
        random_state=LDA_RANDOM_STATE,
        n_jobs=1,
    )

    document_topic_distributions = lda_model.fit_transform(
        document_term_matrix
    )

    # -----------------------------------------
    # STEP 3: Extract topic keywords
    # -----------------------------------------

    topics = []

    for topic_index, topic_word_weights in enumerate(
        lda_model.components_
    ):
        # Get indices of top words sorted by weight.
        top_word_indices = topic_word_weights.argsort()[
            -top_words:
        ][::-1]

        keywords = []
        for word_index in top_word_indices:
            keywords.append({
                "word": feature_names[word_index],
                "weight": round(
                    float(topic_word_weights[word_index]), 4
                ),
            })

        topics.append({
            "topic_id": topic_index + 1,
            "label": f"Topic {topic_index + 1}",
            "keywords": keywords,
            "top_words": [kw["word"] for kw in keywords],
        })

    # -----------------------------------------
    # STEP 4: Document-topic assignments
    # -----------------------------------------

    document_topics = []

    for doc_index, distribution in enumerate(
        document_topic_distributions
    ):
        dominant_topic = int(np.argmax(distribution))

        document_topics.append({
            "document_index": doc_index,
            "dominant_topic": dominant_topic + 1,
            "topic_distribution": [
                round(float(prob), 4) for prob in distribution
            ],
        })

    # -----------------------------------------
    # STEP 5: Model quality metrics
    # -----------------------------------------

    log_likelihood = float(lda_model.score(document_term_matrix))
    perplexity = float(lda_model.perplexity(document_term_matrix))

    return {
        "success": True,
        "num_topics": num_topics,
        "num_documents": len(cleaned_documents),
        "vocabulary_size": len(feature_names),
        "topics": topics,
        "document_topics": document_topics,
        "model_metrics": {
            "log_likelihood": round(log_likelihood, 4),
            "perplexity": round(perplexity, 4),
        },
    }


# --------------------------------------------------
# SINGLE DOCUMENT TOPIC EXTRACTION
# --------------------------------------------------

def extract_topics_from_text(
    text,
    num_topics=DEFAULT_NUM_TOPICS,
    top_words=DEFAULT_TOP_WORDS,
    segment_size=500,
):
    """
    Extract topics from a single document by splitting it
    into segments and applying LDA.

    This is the main entry point for the API endpoint.

    Args:
        text (str): Full document text.
        num_topics (int): Number of topics to discover.
        top_words (int): Number of keywords per topic.
        segment_size (int): Characters per text segment.

    Returns:
        dict: Topic modeling results.
    """

    if not isinstance(text, str) or not text.strip():
        raise ValueError("Please provide non-empty text for topic modeling.")

    # Split document into segments.
    segments = split_into_segments(
        text,
        segment_size=segment_size,
    )

    if len(segments) < 2:
        raise ValueError(
            "The document is too short for topic modeling. "
            "Please provide a longer document with more content."
        )

    return extract_topics(
        documents=segments,
        num_topics=num_topics,
        top_words=top_words,
    )


# --------------------------------------------------
# TF-IDF KEYWORD EXTRACTION
# --------------------------------------------------

def extract_tfidf_keywords(
    documents,
    top_n=20,
):
    """
    Extract the most important keywords from documents
    using TF-IDF weighting.

    Args:
        documents (list): List of text strings.
        top_n (int): Number of top keywords to return.

    Returns:
        dict: Top keywords with their TF-IDF scores.
    """

    if not isinstance(documents, list) or not documents:
        raise ValueError("Please provide a non-empty list of documents.")

    cleaned = [
        preprocess_for_topics(doc)
        for doc in documents
        if isinstance(doc, str) and doc.strip()
    ]

    if not cleaned:
        raise ValueError("No valid documents found for keyword extraction.")

    tfidf_vectorizer = TfidfVectorizer(
        max_features=MAX_FEATURES,
        stop_words="english",
        token_pattern=r"\b[a-z]{3,}\b",
    )

    tfidf_matrix = tfidf_vectorizer.fit_transform(cleaned)
    feature_names = tfidf_vectorizer.get_feature_names_out()

    # Average TF-IDF score across all documents.
    mean_scores = np.asarray(tfidf_matrix.mean(axis=0)).flatten()

    top_indices = mean_scores.argsort()[-top_n:][::-1]

    keywords = []
    for index in top_indices:
        if mean_scores[index] > 0:
            keywords.append({
                "word": feature_names[index],
                "tfidf_score": round(float(mean_scores[index]), 4),
            })

    return {
        "success": True,
        "total_features": len(feature_names),
        "top_keywords": keywords,
    }
