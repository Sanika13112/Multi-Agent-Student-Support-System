
from pathlib import Path

from modules.common.document_loader import load_document
from modules.quick_notes.content_classifier import classify_document


PDF_PATH = "data/DAA_Unit5_Computational_Complexity.pdf"


def main():

    document = load_document(PDF_PATH)

    # Support loaders that return either text or a dictionary.
    if isinstance(document, dict):
        text = document.get("text", "")
    else:
        text = document

    if not isinstance(text, str) or not text.strip():
        raise ValueError("No document text was extracted.")

    result = classify_document(text)

    for category, items in result.items():

        print(f"\n========== {category.upper()} ==========")

        for index, item in enumerate(items, start=1):
            print(f"{index}. {item}")

        print("Total:", len(items))


if __name__ == "__main__":
    main()
