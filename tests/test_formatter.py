
from modules.quick_notes.formatter import format_study_notes


sample_content = {
    "definitions": [
        "P represents problems solvable in polynomial time."
    ],
    "examples": [
        "Example: Binary search and merge sort."
    ],
    "formulas": [
        "Time Complexity = O(n)"
    ],
    "algorithms": [
        "Step 1: Input the problem.",
        "Step 2: Process the input.",
        "Step 3: Return the result."
    ],
    "important_points": [
        "P is the class of polynomial-time solvable problems.",
        "NP is the class of problems with polynomial-time verifiable solutions."
    ]
}

sample_diagrams = [
    {
        "page": 2,
        "filename": "page_2_image_1.png",
        "url": "/static/generated/sample/page_2_image_1.png"
    }
]

generated_diagrams = [
    {
        "title": "Complexity Classes",
        "type": "concept_map",
        "mermaid": (
            "flowchart TD\n"
            'A["Complexity Classes"] --> B["P"]\n'
            'A --> C["NP"]'
        )
    }
]

notes = format_study_notes(
    document_name="DAA Unit 5",
    classified_content=sample_content,
    original_diagrams=sample_diagrams,
    generated_diagrams=generated_diagrams
)

print(notes)

with open(
    "test_formatted_notes.md",
    "w",
    encoding="utf-8"
) as file:
    file.write(notes)

print("\nFormatted notes saved successfully.")
