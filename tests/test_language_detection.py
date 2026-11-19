
from pathlib import Path
import fasttext

# Locate the downloaded model
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "models" / "lid.176.ftz"

if not MODEL_PATH.exists():
    raise FileNotFoundError(f"Language model not found: {MODEL_PATH}")

print("Loading language detection model...")
model = fasttext.load_model(str(MODEL_PATH))

# Sample notice text
text = """
All candidates are hereby informed that document
verification will take place on 12 September 2024.
Candidates must report at 9 AM.
"""

# fastText expects a single line
text = " ".join(text.split())

labels, probabilities = model.predict(text, k=3)

print("\n--- LANGUAGE DETECTION RESULT ---")

language_names = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi"
}

for label, probability in zip(labels, probabilities):
    code = label.replace("__label__", "")
    name = language_names.get(code, "Other language")

    print(f"{name} ({code}): {probability:.2%}")

print("\nLanguage detection completed!")
