"""
MyMemory translation for the Notice Translator (cloud service).

MyMemory answers from two places:
  - its translation memory: sentences that people translated before, and
  - machine translation (MT).
For unclear input it can return a stored translation of a DIFFERENT
sentence that only looks similar (e.g. a museum name for a garbled OCR
line). choose_translation() detects that and uses the MT answer instead.
"""

import json
import re
import html
import os
from difflib import SequenceMatcher
import urllib.parse
import urllib.request
import urllib.error


API_URL = "https://api.mymemory.translated.net/get"

SUPPORTED_LANGUAGES = {"en", "hi", "mr"}
MAX_QUERY_BYTES = 450

# A stored translation is used only if its source sentence is at least this
# similar to ours (1.0 = identical).
MIN_MEMORY_SIMILARITY = 0.85


class TranslationError(Exception):
    """Raised when MyMemory translation fails."""


def split_text(text, max_bytes=MAX_QUERY_BYTES):
    """Split text into UTF-8-safe chunks without exceeding the API limit."""

    words = re.findall(r"\S+\s*|\s+", text)
    chunks = []
    current = ""

    for word in words:
        if len((current + word).encode("utf-8")) <= max_bytes:
            current += word
            continue

        if current:
            chunks.append(current)
            current = ""

        # Handle an unusually long word.
        remaining = word

        while len(remaining.encode("utf-8")) > max_bytes:
            piece = ""
            for character in remaining:
                if len((piece + character).encode("utf-8")) > max_bytes:
                    break
                piece += character

            if not piece:
                raise TranslationError("Unable to split the text safely.")

            chunks.append(piece)
            remaining = remaining[len(piece):]

        current = remaining

    if current:
        chunks.append(current)

    return chunks


def _normalise(text):
    """Lower-case and collapse spaces, for comparing sentences."""
    return " ".join(str(text or "").lower().split())


def _is_machine_translation(match):
    """MyMemory marks machine-translated entries with created-by 'MT!'."""
    return str(match.get("created-by", "")).upper().startswith("MT")


def choose_translation(query, result):
    """
    Pick the translation to trust from a MyMemory response.

    1. Start with MyMemory's main answer (responseData.translatedText).
    2. Find which entry in "matches" produced it. If that entry is a stored
       translation of a different sentence (similarity below
       MIN_MEMORY_SIMILARITY), replace it with the machine translation entry.
    3. If the response has no "matches" list, keep the main answer.
    """

    main_answer = result.get("responseData", {}).get("translatedText", "")
    matches = [m for m in (result.get("matches") or []) if isinstance(m, dict)]

    if not matches:
        return main_answer

    source = next((m for m in matches if m.get("translation") == main_answer), None)

    if source is None or _is_machine_translation(source):
        return main_answer

    similarity = SequenceMatcher(None, _normalise(source.get("segment")), _normalise(query)).ratio()

    if similarity >= MIN_MEMORY_SIMILARITY:
        return main_answer

    machine = next((m for m in matches if _is_machine_translation(m) and m.get("translation")), None)
    return machine["translation"] if machine else main_answer


def translate_chunk(text, source_language, target_language):
    """Translate one text segment using MyMemory."""

    params = {
        "q": text,
        "langpair": f"{source_language}|{target_language}",
        "mt": "1"
    }

    # Optional: supplying an email increases the documented daily allowance.
    contact_email = os.getenv("MYMEMORY_EMAIL", "").strip()

    if contact_email:
        params["de"] = contact_email

    query_string = urllib.parse.urlencode(params)

    request = urllib.request.Request(
        f"{API_URL}?{query_string}",
        headers={
            "Accept": "application/json",
            "User-Agent": "StudyMateAI-NoticeTranslator/1.0"
        }
    )

    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            result = json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as error:
        if error.code in (429, 403):
            raise TranslationError(
                "MyMemory usage limit reached or access denied. "
                "Please try again later."
            )

        raise TranslationError(
            f"MyMemory returned HTTP error {error.code}."
        )

    except urllib.error.URLError:
        raise TranslationError(
            "Unable to connect to MyMemory. Check your internet connection."
        )

    except (TimeoutError, json.JSONDecodeError):
        raise TranslationError(
            "The translation service did not return a valid response."
        )

    if result.get("responseStatus") != 200:
        raise TranslationError(
            result.get("responseDetails") or "Translation was unsuccessful."
        )

    translated = choose_translation(text, result)

    if not translated:
        raise TranslationError("MyMemory returned an empty translation.")

    return html.unescape(translated)


def translate_text(text, source_language, target_language):
    """Translate complete text, splitting it into API-sized segments."""

    text = text.strip()

    if not text:
        raise ValueError("Please provide text to translate.")

    if source_language not in SUPPORTED_LANGUAGES:
        raise ValueError("Unsupported source language.")

    if target_language not in SUPPORTED_LANGUAGES:
        raise ValueError("Unsupported target language.")

    if source_language == target_language:
        return text

    chunks = split_text(text)

    translated_chunks = []

    for chunk in chunks:
        translated_chunks.append(
            translate_chunk(
                chunk,
                source_language,
                target_language
            )
        )

    return "".join(translated_chunks)