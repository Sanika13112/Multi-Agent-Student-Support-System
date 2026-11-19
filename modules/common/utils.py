
"""
Common Utility Functions

Purpose:
Provide reusable helper functions for all
modules in the Student Support System.
"""

import re
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
