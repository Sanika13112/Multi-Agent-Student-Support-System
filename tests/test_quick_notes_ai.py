
from modules.quick_notes.service import (
    prepare_study_document,
    generate_study_notes
)


def main():

    print("===== QUICKNOTES AI TEST =====")

    file_path = "data/DAA_Unit5_Computational_Complexity.pdf"

    print("\nLoading document...")

    document = prepare_study_document(file_path)

    print("Filename:", document["filename"])
    print("Pages:", document["page_count"])
    print("Chunks:", document["chunk_count"])

    print("\nGenerating AI study notes...")

    result = generate_study_notes(
        document_text=document["text"],
        filename=document["filename"]
    )

    print("\n===== GENERATED STUDY NOTES =====")
    print(result["notes"])

    print("\nSections processed:", result["sections_processed"])
    print("Model:", result["model"])

    print("\nQuickNotes AI test completed!")


if __name__ == "__main__":
    main()
