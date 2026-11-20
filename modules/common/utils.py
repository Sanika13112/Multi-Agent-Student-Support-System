
"""
Common Utility Functions

Purpose:
Provide reusable helper functions for all
modules in the Student Support System.
"""

import re
import json
import hashlib

from pathlib import Path


def clean_text(text):
    """
    Remove unnecessary spaces and formatting
    from extracted text.
    """

    if not isinstance(text, str):
        raise TypeError("Input must be a string.")

    # Replace multiple spaces and newlines with one space.
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def validate_text(text):
    """
    Check whether the supplied text is valid.
    """

    if not isinstance(text, str):
        return False

    return bool(text.strip())


def format_file_size(size_bytes):
    """
    Convert file size from bytes into a readable format.
    """

    size_kb = size_bytes / 1024

    if size_kb < 1024:
        return f"{size_kb:.2f} KB"

    size_mb = size_kb / 1024

    return f"{size_mb:.2f} MB"


def chunk_text(text, chunk_size=1000, overlap=150):
    """
    Divide long text into smaller overlapping chunks.

    chunk_size: Maximum number of characters per chunk.
    overlap: Number of characters shared between chunks.
    """

    if not isinstance(text, str):
        raise TypeError("Input must be a string.")

    if chunk_size <= 0:
        raise ValueError("Chunk size must be positive.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("Overlap must be smaller than chunk size.")

    # Clean the original text.
    text = clean_text(text)

    chunks = []

    start = 0

    while start < len(text):

        end = min(start + chunk_size, len(text))

        chunks.append(text[start:end])

        # Move forward while retaining some previous text.
        start += chunk_size - overlap

    return chunks


def calculate_file_hash(file_path):
    """
    Generate a SHA-256 hash for a file.

    Useful for identifying identical uploaded files.
    """

    path = Path(file_path)

    if not path.exists() or not path.is_file():
        raise FileNotFoundError("File does not exist.")

    sha256 = hashlib.sha256()

    with open(path, "rb") as file:

        # Read the file in small blocks.
        for block in iter(lambda: file.read(4096), b""):

            sha256.update(block)

    return sha256.hexdigest()


def parse_ai_json(text):
    """
    Turn an LLM reply into a Python dict.

    Steps:
    1. Remove ```json code fences if the model added them.
    2. Keep only the part from the first "{" to the last "}".
    3. Parse it. If that fails, remove trailing commas
       ({"a": 1,} or [1, 2,]), the most common small-model mistake,
       and parse again.

    Raises:
        ValueError: the reply is still not a valid JSON object.
    """

    if not isinstance(text, str) or not text.strip():
        raise ValueError("The AI returned an empty response.")

    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("The AI did not return a JSON object.")

    json_text = cleaned[start:end + 1]

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        repaired = re.sub(r",\s*([}\]])", r"\1", json_text)
        try:
            data = json.loads(repaired)
        except json.JSONDecodeError as error:
            raise ValueError(f"The AI returned invalid JSON ({error.msg}).") from error

    if not isinstance(data, dict):
        raise ValueError("The AI did not return a JSON object.")

    return data
