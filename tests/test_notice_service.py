from pathlib import Path
import sys

# Add the project root to Python's import path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from modules.notice_translator import process_notice

image_path = input(
    "Enter the full path of your notice image: "
).strip().strip('"').strip("'")

try:
    result = process_notice(image_path)

    print("\n========== NOTICE PROCESSING RESULT ==========")

    print("\n--- EXTRACTED TEXT ---")
    print(result["extracted_text"])

    print("\n--- LANGUAGE DETECTION ---")

    language = result["language"]

    print(
        "Primary language:",
        language["primary_language_name"]
    )

    print(
        "Confidence:",
        f'{language["confidence"]:.2%}'
    )

    print(
        "Mixed language:",
        language["is_mixed"]
    )

    print(
        "Detected languages:",
        language["detected_languages"]
    )

    print("\n--- LANGUAGE DISTRIBUTION ---")

    for name, percentage in language[
        "language_distribution"
    ].items():
        print(f"{name}: {percentage}%")

    print("\nProcessing completed successfully!")

except Exception as error:
    print("\nProcessing failed:", error)
