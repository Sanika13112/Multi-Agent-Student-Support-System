"""
Multilingual NLP Module (CO3)

Purpose:
    1. Detect the language of a document (English, Hindi, Marathi, ...).
    2. Translate text into Hindi or Marathi with a cloud translation service.

Technologies:
    - fastText lid.176 model (models/lid.176.ftz): offline language
      identification for 176 languages, already used by Notice Translator.
    - MyMemory Translation API (cloud-based AI service, free tier), through
      modules/notice_translator/translation.py.

If the fastText package is not installed, detection falls back to counting
Unicode scripts (Latin vs Devanagari) and says so in the "method" field,
so the result is never presented as more precise than it is.

CO Mapping: CO3 - Implementation of topic modeling or multilingual NLP
            using appropriate NLP techniques and cloud-based AI services.
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LANGUAGE_MODEL_PATH = PROJECT_ROOT / "models" / "lid.176.ftz"

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
}

# Languages the cloud translator supports in this project.
TRANSLATION_TARGETS = {"hi": "Hindi", "mr": "Marathi"}

# MyMemory accepts about 500 bytes per request, so long text is split into
# many requests. We translate at most this many characters per run.
MAX_TRANSLATION_CHARS = 1200

_fasttext_model = None


# --------------------------------------------------
# LANGUAGE DETECTION
# --------------------------------------------------

def _load_fasttext():
    """Load the fastText model once. Returns None if fastText is unavailable."""

    global _fasttext_model

    if _fasttext_model is None:
        try:
            import fasttext
        except ImportError:
            return None

        if not LANGUAGE_MODEL_PATH.exists():
            return None

        _fasttext_model = fasttext.load_model(str(LANGUAGE_MODEL_PATH))

    return _fasttext_model


def fasttext_predict(model, text, k=3):
    """
    Return [(label, probability), ...] from fastText.

    fastText's predict() breaks with NumPy 2 ("Unable to avoid copy while
    creating an array"). In that case we call the underlying C++ predictor
    directly, which returns the same (probability, label) pairs.
    Also used by modules/notice_translator/service.py.
    """

    try:
        labels, probabilities = model.predict(text, k=k)
        return list(zip(labels, probabilities))
    except ValueError:
        pairs = model.f.predict(text, k, 0.0, "strict")
        return [(label, probability) for probability, label in pairs]


def _script_counts(text):
    """Count Latin and Devanagari letters (used by the fallback detector)."""

    latin = len(re.findall(r"[A-Za-z]", text))
    devanagari = len(re.findall(r"[ऀ-ॿ]", text))
    return latin, devanagari


def detect_language(text, sample_chars=3000):
    """
    Detect the main language of the text.

    Returns:
        dict: code, name, confidence (0-1), method, top_predictions,
              and the share of Latin vs Devanagari letters.
    """

    if not isinstance(text, str) or not text.strip():
        raise ValueError("Please provide text for language detection.")

    # fastText expects one line; a few thousand characters is plenty.
    sample = " ".join(text.split())[:sample_chars]
    latin, devanagari = _script_counts(sample)
    letters = max(latin + devanagari, 1)

    scripts = {
        "latin_percent": round(latin / letters * 100, 1),
        "devanagari_percent": round(devanagari / letters * 100, 1),
    }

    model = _load_fasttext()

    if model is not None:
        predictions = [
            {
                "code": label.replace("__label__", ""),
                "name": LANGUAGE_NAMES.get(label.replace("__label__", ""), "Other"),
                "confidence": round(float(probability), 4),
            }
            for label, probability in fasttext_predict(model, sample, k=3)
        ]
        best = predictions[0]
        return {
            "code": best["code"],
            "name": best["name"],
            "confidence": best["confidence"],
            "method": "fastText lid.176",
            "top_predictions": predictions,
            "scripts": scripts,
        }

    # Fallback: script counting. Devanagari is shared by Hindi and Marathi,
    # so this method cannot tell those two apart and reports both.
    if devanagari > latin:
        code, name = "hi/mr", "Hindi or Marathi (Devanagari script)"
    else:
        code, name = "en", "English (Latin script)"

    return {
        "code": code,
        "name": name,
        "confidence": round(max(latin, devanagari) / letters, 4),
        "method": "script counting (fastText not installed)",
        "top_predictions": [],
        "scripts": scripts,
    }


# --------------------------------------------------
# CLOUD TRANSLATION
# --------------------------------------------------

def translate(text, target_language, source_language="en"):
    """
    Translate text with the MyMemory cloud API.

    Raises:
        ValueError: unsupported language or empty text.
        RuntimeError: the cloud service failed (no internet, daily limit...).
    """

    if target_language not in TRANSLATION_TARGETS:
        raise ValueError("Translation target must be 'hi' (Hindi) or 'mr' (Marathi).")

    text = (text or "").strip()[:MAX_TRANSLATION_CHARS]

    if not text:
        raise ValueError("Nothing to translate.")

    from modules.notice_translator.translation import TranslationError, translate_text

    try:
        translated = translate_text(text, source_language, target_language)
    except TranslationError as error:
        raise RuntimeError(f"MyMemory translation failed: {error}") from error

    return {
        "service": "MyMemory Translation API (cloud)",
        "source_language": source_language,
        "target_language": target_language,
        "target_language_name": TRANSLATION_TARGETS[target_language],
        "source_text": text,
        "translated_text": translated,
    }
