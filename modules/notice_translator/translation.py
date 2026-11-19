import json
import re
import html
import os
import urllib.parse
import urllib.request
import urllib.error


API_URL = "https://api.mymemory.translated.net/get"

SUPPORTED_LANGUAGES = {"en", "hi", "mr"}
MAX_QUERY_BYTES = 450


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

    translated = result.get("responseData", {}).get("translatedText", "")

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