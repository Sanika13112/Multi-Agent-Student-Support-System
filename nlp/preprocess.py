
"""
Text Preprocessing Module

Purpose:
This module cleans student questions before they are
given to the Machine Learning model.

Technologies:
- re: Removes unwanted characters.
- NLTK: Tokenizes text and provides English stop words.
"""

# re is Python's regular expression module.
# It helps us find and replace unwanted characters.
import re

# word_tokenize divides text into individual word tokens.
# preserve_line=True avoids needing a separate Punkt download.
from nltk.tokenize import word_tokenize

# stopwords provides a predefined list of common English words.
from nltk.corpus import stopwords


# Load the English stop-word list once when this module is imported.
# Loading it once avoids repeating the same operation for every question.
ENGLISH_STOP_WORDS = set(stopwords.words("english"))


# Keep these words because they can change the meaning
# or purpose of a student's question.
IMPORTANT_WORDS = {
    "not", "no", "never", "nor",
    "what", "how", "why", "when",
    "where", "which"
}


def clean_text(text):
    """
    Convert the input into clean, lowercase text.

    Steps:
    1. Convert uppercase letters into lowercase.
    2. Remove unnecessary special characters.
    3. Replace repeated spaces with a single space.

    Args:
        text (str): Original student question.

    Returns:
        str: Cleaned text.
    """

    # Convert the input to lowercase.
    text = text.lower()

    # Keep only English letters, numbers, and spaces.
    # Replace other characters with spaces.
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    # Remove extra spaces from the text.
    text = re.sub(r"\s+", " ", text).strip()

    return text


def tokenize_text(text):
    """
    Divide the cleaned sentence into individual words.

    Args:
        text (str): Cleaned sentence.

    Returns:
        list: List of word tokens.
    """

    # NLTK splits the sentence into individual word tokens.
    tokens = word_tokenize(text, preserve_line=True)

    return tokens


def remove_stopwords(tokens):
    """
    Remove common English words that are less useful
    for our basic intent-classification pipeline.

    Important:
    Negation words and question words are preserved
    because they may change the meaning of a question.

    Args:
        tokens (list): List of word tokens.

    Returns:
        list: Filtered tokens.
    """

    filtered_tokens = []

    for word in tokens:

        # Keep important words even if they appear in
        # the standard English stop-word list.
        if word in IMPORTANT_WORDS:
            filtered_tokens.append(word)

        # Keep other words that are not stop words.
        elif word not in ENGLISH_STOP_WORDS:
            filtered_tokens.append(word)

    return filtered_tokens


def preprocess_text(text):
    """
    Perform the complete text preprocessing pipeline.

    Processing order:
    Original text -> Cleaning -> Tokenization -> Stop-word removal.

    Args:
        text (str): Student's original question.

    Returns:
        list: Processed tokens ready for further NLP processing.
    """

    # Validate the input before processing.
    if not isinstance(text, str):
        raise TypeError("Input must be a string.")

    # Clean the original sentence.
    cleaned_text = clean_text(text)

    # Convert the cleaned sentence into word tokens.
    tokens = tokenize_text(cleaned_text)

    # Remove unnecessary stop words.
    processed_tokens = remove_stopwords(tokens)

    return processed_tokens


# =========================================
# TF-IDF VECTORIZATION (CO1)
# =========================================

# scikit-learn provides TfidfVectorizer for converting
# text documents into numerical TF-IDF feature vectors.
from sklearn.feature_extraction.text import TfidfVectorizer


def vectorize_text(texts, max_features=5000):
    """
    Convert a list of text documents into TF-IDF vectors.

    TF-IDF (Term Frequency - Inverse Document Frequency)
    assigns higher weights to words that are important
    in a specific document but rare across all documents.

    Args:
        texts (list): List of text strings to vectorize.
        max_features (int): Maximum number of features.

    Returns:
        dict: Contains:
            - vectors: TF-IDF matrix (sparse).
            - feature_names: List of feature words.
            - shape: Dimensions of the TF-IDF matrix.
            - vectorizer: Fitted TfidfVectorizer instance
              (can be reused for new documents).
    """

    if not isinstance(texts, list) or not texts:
        raise ValueError("Input must be a non-empty list of texts.")

    # Preprocess each text using our cleaning pipeline.
    cleaned_texts = []

    for text in texts:
        if isinstance(text, str) and text.strip():
            cleaned_texts.append(clean_text(text))

    if not cleaned_texts:
        raise ValueError("No valid texts found after cleaning.")

    # Create and fit the TF-IDF vectorizer.
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.95,
    )

    tfidf_matrix = vectorizer.fit_transform(cleaned_texts)

    feature_names = vectorizer.get_feature_names_out().tolist()

    return {
        "vectors": tfidf_matrix,
        "feature_names": feature_names,
        "shape": tfidf_matrix.shape,
        "vectorizer": vectorizer,
    }
