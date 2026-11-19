"""Flask routes for VoiceSnap."""
import os
import secrets
import tempfile
from pathlib import Path

from flask import (
    Blueprint, current_app, jsonify, render_template, request, session,
    send_file,
)

from .service import (
    transcribe_audio, save_transcript, get_transcript,
    generate_study_notes, clear_transcript,
)

voice_snap_bp = Blueprint("voice_snap", __name__)
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm", ".mp4"}
MAX_AUDIO_BYTES = 100 * 1024 * 1024


def _session_id():
    if "voicesnap_session_id" not in session:
        session["voicesnap_session_id"] = secrets.token_urlsafe(24)
    return session["voicesnap_session_id"]


@voice_snap_bp.get("/voice-snap")
def voice_snap_page():
    return render_template("voice_snap.html")


@voice_snap_bp.post("/api/voice-snap/upload")
def voice_snap_upload():
    uploaded = request.files.get("audio")
    if uploaded is None or not uploaded.filename:
        return jsonify(success=False, message="Choose an audio file first."), 400

    suffix = Path(uploaded.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        return jsonify(
            success=False,
            message="Unsupported audio format. Use MP3, WAV, M4A, FLAC, OGG, WEBM or MP4."
        ), 400

    temp_path = None
    try:
        data = uploaded.read(MAX_AUDIO_BYTES + 1)
        if not data:
            return jsonify(success=False, message="The selected audio file is empty."), 400
        if len(data) > MAX_AUDIO_BYTES:
            return jsonify(success=False, message="Audio file exceeds the 100 MB limit."), 413

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(data)
            temp_path = temp_file.name

        result = transcribe_audio(temp_path)
        session_id = _session_id()
        save_transcript(session_id, Path(uploaded.filename).name, result)

        return jsonify(
            success=True,
            message="Audio transcribed successfully.",
            filename=Path(uploaded.filename).name,
            transcript=result["transcript"],
            segments=result["segments"],
            language=result["language"],
            duration=result["duration"],
        )
    except ValueError as exc:
        return jsonify(success=False, message=str(exc)), 422
    except Exception:
        current_app.logger.exception("VoiceSnap transcription failed")
        return jsonify(
            success=False,
            message="Transcription failed. Check that Faster-Whisper is installed and the audio file is valid."
        ), 500
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                current_app.logger.warning("Could not remove temporary VoiceSnap audio file.")


@voice_snap_bp.post("/api/voice-snap/notes")
def voice_snap_notes():
    payload = request.get_json(silent=True) or {}
    mode = (payload.get("mode") or "detailed").strip().lower()
    item = get_transcript(_session_id())
    if not item:
        return jsonify(success=False, message="Upload and transcribe audio before generating notes."), 400

    try:
        notes = generate_study_notes(item["transcript"], mode)
        # Update the in-memory session record without changing its transcript.
        from . import service
        with service._store_lock:
            if _session_id() in service._TRANSCRIPTS:
                service._TRANSCRIPTS[_session_id()]["notes"][mode] = notes
        return jsonify(success=True, mode=mode, notes=notes)
    except ValueError as exc:
        return jsonify(success=False, message=str(exc)), 400
    except Exception:
        current_app.logger.exception("VoiceSnap notes generation failed")
        return jsonify(
            success=False,
            message="Notes generation failed. Make sure Ollama is running and the configured Qwen model is available."
        ), 500


@voice_snap_bp.get("/api/voice-snap/transcript")
def voice_snap_get_transcript():
    item = get_transcript(_session_id())
    if not item:
        return jsonify(success=True, available=False)
    return jsonify(
        success=True,
        available=True,
        filename=item["filename"],
        transcript=item["transcript"],
        language=item.get("language"),
        duration=item.get("duration"),
    )


@voice_snap_bp.get("/api/voice-snap/download")
def voice_snap_download():
    mode = (request.args.get("mode") or "detailed").strip().lower()
    if mode not in {"quick", "detailed"}:
        return jsonify(success=False, message="Invalid notes mode."), 400
    item = get_transcript(_session_id())
    if not item or not item.get("notes", {}).get(mode):
        return jsonify(success=False, message="Generate notes before downloading."), 404

    content = (
        f"VoiceSnap - {mode.title()} Notes\n"
        f"Audio: {item['filename']}\n"
        f"Language: {item.get('language') or 'Unknown'}\n"
        f"Duration: {item.get('duration') or 0} seconds\n"
        + "=" * 60 + "\n\n"
        + item["notes"][mode]
    )
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".md", delete=False
    ) as temp_file:
        temp_file.write(content)
        path = temp_file.name

    response = send_file(
        path,
        as_attachment=True,
        download_name=f"voicesnap_{mode}_notes.md",
        mimetype="text/markdown",
    )
    response.call_on_close(lambda: os.path.exists(path) and os.remove(path))
    return response


@voice_snap_bp.post("/api/voice-snap/reset")
def voice_snap_reset():
    clear_transcript(_session_id())
    return jsonify(success=True, message="VoiceSnap session cleared.")
