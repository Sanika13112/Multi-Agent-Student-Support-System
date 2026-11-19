"""Local audio transcription and AI note-generation service."""
from __future__ import annotations

import threading
from typing import Dict, Any

from faster_whisper import WhisperModel
from modules.common.ai_client import generate_response

WHISPER_MODEL_SIZE = "base"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"
MAX_TRANSCRIPT_CHARS = 30000

_whisper_model = None
_model_lock = threading.Lock()
_store_lock = threading.RLock()
_TRANSCRIPTS: Dict[str, Dict[str, Any]] = {}


def get_whisper_model():
    """Load Faster-Whisper once, using CPU/int8 for broad Windows compatibility."""
    global _whisper_model
    if _whisper_model is None:
        with _model_lock:
            if _whisper_model is None:
                _whisper_model = WhisperModel(
                    WHISPER_MODEL_SIZE,
                    device=WHISPER_DEVICE,
                    compute_type=WHISPER_COMPUTE_TYPE,
                )
    return _whisper_model


def transcribe_audio(file_path: str) -> Dict[str, Any]:
    """Transcribe an audio file and return text plus timestamped segments."""
    model = get_whisper_model()
    segments, info = model.transcribe(
        file_path,
        beam_size=3,
        vad_filter=True,
        condition_on_previous_text=False,
    )

    segment_items = []
    transcript_parts = []
    for segment in segments:
        text = (segment.text or "").strip()
        if not text:
            continue
        transcript_parts.append(text)
        segment_items.append({
            "start": round(float(segment.start), 2),
            "end": round(float(segment.end), 2),
            "text": text,
        })

    transcript = " ".join(transcript_parts).strip()
    if not transcript:
        raise ValueError(
            "No speech could be detected. Try a clearer recording with audible speech."
        )

    return {
        "transcript": transcript,
        "segments": segment_items,
        "language": getattr(info, "language", None),
        "duration": round(float(getattr(info, "duration", 0) or 0), 2),
    }


def save_transcript(session_id: str, filename: str, result: Dict[str, Any]) -> None:
    with _store_lock:
        _TRANSCRIPTS[session_id] = {
            "filename": filename,
            **result,
            "notes": {},
        }


def get_transcript(session_id: str):
    with _store_lock:
        item = _TRANSCRIPTS.get(session_id)
        return dict(item) if item else None


def clear_transcript(session_id: str) -> None:
    with _store_lock:
        _TRANSCRIPTS.pop(session_id, None)


def generate_study_notes(transcript: str, mode: str = "detailed") -> str:
    """Generate transcript-grounded notes using the project's local Qwen client."""
    if not transcript or not transcript.strip():
        raise ValueError("There is no transcript available. Upload audio first.")

    mode = mode.lower().strip()
    if mode not in {"quick", "detailed"}:
        raise ValueError("Notes mode must be 'quick' or 'detailed'.")

    clipped_transcript = transcript[:MAX_TRANSCRIPT_CHARS]
    if mode == "quick":
        instructions = """
Create concise revision notes from the transcript.
Use a suitable title, 5-12 key points, important definitions/formulas if spoken,
and a short revision summary. Keep the notes compact.
"""
    else:
        instructions = """
Create well-organized study notes from the transcript.
Include a suitable title, overview, headings and subheadings, explanations,
important definitions, examples, formulas, key takeaways and a conclusion
where the transcript supports them. Do not add unsupported sections.
"""

    system_prompt = """
You are VoiceSnap, a careful lecture-notes assistant for B.Tech students.
Use ONLY the supplied transcript. Do not add facts from outside knowledge.
Do not invent missing definitions, formulas, examples, names or numbers.
Preserve technical terms and the speaker's intended meaning.
If a phrase is unclear, mark it as unclear rather than guessing.
Write in simple, clear English with readable Markdown headings and bullets.
"""

    prompt = f"""
TASK:
{instructions}

SOURCE TRANSCRIPT:
------------------
{clipped_transcript}
------------------

Generate {mode} study notes based only on this transcript.
"""
    answer = generate_response(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.2,
        max_tokens=900 if mode == "quick" else 1600,
    )
    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError("The local AI model returned an empty notes response.")
    return answer.strip()
