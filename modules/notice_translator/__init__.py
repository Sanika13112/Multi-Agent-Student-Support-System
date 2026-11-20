"""
Notice Translator package.

service.py imports EasyOCR (which loads PyTorch), so it is loaded only when
one of its functions is first used. This keeps
`from modules.notice_translator.translation import translate_text`
fast for the NLP pipeline, which translates text but never runs OCR.

`from modules.notice_translator import process_notice` works exactly as before.
"""

__all__ = [
    "process_notice",
    "extract_notice_text",
    "detect_languages",
]


def __getattr__(name):
    """Load service.py the first time one of its functions is requested (PEP 562)."""

    if name in __all__:
        from . import service
        return getattr(service, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
