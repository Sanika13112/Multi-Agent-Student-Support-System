
"""
Common Document Loader

Purpose:
Extract text from PDF and TXT documents.

Used by:
1. QuickNotes
2. AskAway
3. BrainCheck
"""

from pathlib import Path
from pypdf import PdfReader


# Supported document formats.
SUPPORTED_EXTENSIONS = {".pdf", ".txt"}

# Maximum allowed file size: 20 MB.
MAX_FILE_SIZE = 20 * 1024 * 1024


class DocumentError(Exception):
    """Raised when a document cannot be processed."""


def validate_document(file_path):
    """
    Check whether a document exists and is supported.
    """

    # Convert the supplied path into a Path object.
    path = Path(file_path)

    # Check whether the file exists.
    if not path.exists():
        raise DocumentError("Document does not exist.")

    # Check whether the path points to a file.
    if not path.is_file():
        raise DocumentError("The provided path is not a file.")

    # Check the file extension.
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise DocumentError("Only PDF and TXT files are supported.")

    # Check the file size.
    if path.stat().st_size > MAX_FILE_SIZE:
        raise DocumentError("Document exceeds the 20 MB size limit.")

    return path


def extract_text_from_pdf(file_path):
    """
    Extract text from every page of a PDF.
    """

    try:
        # Open the PDF document.
        reader = PdfReader(str(file_path))

        # Store extracted text from each page.
        page_texts = []

        for page_number, page in enumerate(reader.pages, start=1):

            # Extract text from the current page.
            text = page.extract_text() or ""

            page_texts.append({
                "page_number": page_number,
                "text": text.strip()
            })

        return page_texts

    except Exception as error:
        raise DocumentError(
            f"Unable to read PDF: {error}"
        ) from error


def extract_text_from_txt(file_path):
    """
    Read text from a TXT document.
    """

    try:
        # Read the file using UTF-8 encoding.
        text = Path(file_path).read_text(encoding="utf-8")

        return [{
            "page_number": 1,
            "text": text.strip()
        }]

    except UnicodeDecodeError as error:
        raise DocumentError(
            "The TXT file must use UTF-8 encoding."
        ) from error

    except OSError as error:
        raise DocumentError(
            f"Unable to read TXT file: {error}"
        ) from error


def load_document(file_path):
    """
    Validate a document and extract its text.

    Returns:
        Dictionary containing filename, file type,
        extracted text, page details and page count.
    """

    # Validate the document before processing.
    path = validate_document(file_path)

    # Identify the document type.
    extension = path.suffix.lower()

    # Extract text based on the file type.
    if extension == ".pdf":
        pages = extract_text_from_pdf(path)
    else:
        pages = extract_text_from_txt(path)

    # Combine text from all pages.
    full_text = "\n\n".join(
        page["text"] for page in pages
    )

    # Reject documents without extractable text.
    if not full_text.strip():
        raise DocumentError(
            "No readable text found. "
            "The document may be scanned or empty."
        )

    # Return structured document information.
    return {
        "filename": path.name,
        "file_type": extension.replace(".", ""),
        "text": full_text,
        "pages": pages,
        "page_count": len(pages)
    }
