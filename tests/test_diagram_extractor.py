
from modules.quick_notes.diagram_extractor import (
    extract_original_diagrams
)


PDF_PATH = (
    "data/DAA_Unit5_Computational_Complexity.pdf"
)


def test_original_diagram_extraction():

    result = extract_original_diagrams(PDF_PATH)

    print("\n========== DIAGRAM EXTRACTION RESULT ==========")

    print("Job ID:", result["job_id"])

    print("Original images:", result["total_images"])

    print(
        "Vector page previews:",
        result["total_vector_previews"]
    )

    print("\nOriginal images:")

    for item in result["original_images"]:
        print(
            "Page:", item["page"],
            "| File:", item["filename"]
        )

    print("\nVector previews:")

    for item in result["vector_previews"]:
        print(
            "Page:", item["page"],
            "| Drawings:", item["drawing_count"],
            "| File:", item["filename"]
        )

    print("\nOutput folder:", result["output_directory"])


if __name__ == "__main__":
    test_original_diagram_extraction()
