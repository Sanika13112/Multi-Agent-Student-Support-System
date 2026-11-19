
"""
StudyMate AI - Multi-Agent Student Support System

Main Flask Application

Modules:
- Dashboard
- AI Assistant
- QuickNotes
- BrainCheck
- Career Guidance
"""

import json
import re
import os
import tempfile
import logging
import uuid
from modules.voice_snap import voice_snap_bp

from pathlib import Path

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    session
)

from flask_cors import CORS
from werkzeug.utils import secure_filename

from agents.supervisor.supervisor import route_student_query

from modules.common.ai_client import (
    generate_response,
    check_ollama_connection
)

from modules.quick_notes.service import (
    prepare_study_document,
    generate_quick_notes,
    generate_detailed_notes
)

from modules.common.database import get_db_connection

from modules.ask_away.service import (
    upload_document,
    ask_question,
    get_document_info,
    clear_document
)


# ==================================================
# 1. APPLICATION CONFIGURATION
# ==================================================

app = Flask(__name__)
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "studymate-local-development-key-change-before-deployment"
)
CORS(app)

BASE_DIR = Path(__file__).resolve().parent

ALLOWED_EXTENSIONS = {"pdf", "txt"}
MAX_FILE_SIZE = 20 * 1024 * 1024

app.config["MAX_CONTENT_LENGTH"] = 101 * 1024 * 1024  # 100 MB audio + multipart overhead

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

logger = logging.getLogger(__name__)
app.register_blueprint(voice_snap_bp)

# ==================================================
# 2. AGENT CONFIGURATION
# ==================================================

AGENT_PROMPTS = {
    "study_explanation": """
You are the Study Explanation Agent of StudyMate AI.

Your responsibility is to help engineering students
understand academic and technical concepts.

Instructions:
- Explain concepts from basic to advanced levels.
- Use simple English.
- Preserve important technical terminology.
- Explain definitions, working principles and applications.
- Give practical examples.
- Use step-by-step explanations.
- Include exam-oriented points when useful.
- Use headings and bullet points for readability.
""",

    "career_guidance": """
You are the Career Guidance Agent of StudyMate AI.

Your responsibility is to help students make informed
career and professional development decisions.

Instructions:
- Understand the student's academic background.
- Suggest relevant career paths.
- Explain required technical and soft skills.
- Provide practical learning roadmaps.
- Help with internship and placement preparation.
- Give realistic and actionable suggestions.
""",

    "interview_preparation": """
You are the Interview Preparation Agent of StudyMate AI.

Your responsibility is to prepare students for
technical interviews and HR interviews.

Instructions:
- Provide interview questions and answers.
- Explain the technical concepts behind answers.
- Include practical examples.
- Organize questions by difficulty.
- Give mock interview questions when requested.
- Provide useful preparation advice.
""",

    "greeting": """
You are StudyMate AI.

Respond warmly and naturally to greetings.
Keep your response short, friendly and welcoming.
""",

    "general_assistant": """
You are StudyMate AI, a helpful academic assistant
for engineering students.

Instructions:
- Answer general student questions.
- Use simple English.
- Preserve technical terminology.
- Give examples when useful.
- Explain step by step when necessary.
- Avoid inventing facts.
"""
}


# ==================================================
# 3. HELPER FUNCTIONS
# ==================================================

def allowed_file(filename):
    """Check whether the uploaded file extension is supported."""

    return (
        bool(filename)
        and "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def create_error_response(message, status_code=400):
    """Return a consistent JSON error response."""

    return jsonify({
        "success": False,
        "message": str(message)
    }), status_code


def get_uploaded_file_size(file_path):
    """Return uploaded file size in bytes."""

    return os.path.getsize(file_path)


def dispatch_student_query(message, routing):
    """Dispatch a student query based on Supervisor classification."""

    intent = routing.get("intent", "unknown")
    agent = routing.get("agent")

    if intent == "quick_notes":
        return {
            "answer": (
                "To generate study notes from your document, "
                "please open the QuickNotes workspace. "
                "Upload your PDF or TXT file and select either "
                "Quick Notes or AI Detailed Notes."
            ),
            "agent": "quick_notes"
        }

    if intent == "voice_snap":
        return {
            "answer": (
                "VoiceSnap is designed to convert audio recordings "
                "into study notes. Open the VoiceSnap module to use "
                "the audio transcription workflow."
            ),
            "agent": "voice_snap"
        }

    if intent == "ask_away":
        return {
            "answer": (
                "Open the AskAway workspace, upload your PDF or TXT "
                "document, and ask questions about its contents."
            ),
            "agent": "ask_away"
        }

    if intent == "brain_check":
        return {
            "answer": (
                "BrainCheck is designed to generate quizzes, "
                "MCQs and practice assessments. Open the BrainCheck "
                "workspace to create a quiz."
            ),
            "agent": "brain_check"
        }

    if agent not in AGENT_PROMPTS:
        agent = "general_assistant"

    answer = generate_response(
        prompt=message,
        system_prompt=AGENT_PROMPTS[agent],
        temperature=0.3,
        max_tokens=1200
    )

    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError(
            "The selected agent returned an empty response."
        )

    return {
        "answer": answer.strip(),
        "agent": agent
    }


# ==================================================
# 4. PAGE ROUTES
# ==================================================

@app.route("/")
def index():
    """Render the dashboard."""
    return render_template("index.html")


@app.route("/assistant")
def assistant():
    """Render the AI Assistant."""
    return render_template("assistant.html")


@app.route("/quick-notes")
def quick_notes():
    """Render the QuickNotes workspace."""
    return render_template("quick_notes.html")


@app.route("/brain-check")
def brain_check():
    """Render the BrainCheck workspace."""
    return render_template("brain_check.html")


@app.route("/career-guidance")
def career_guidance():
    """Render the Career Guidance workspace."""
    return render_template("career_guidance.html")


@app.route("/ask-away")
def ask_away():
    """Render the AskAway document chatbot workspace."""
    return render_template("ask_away.html")

@app.route("/notice-translator")
def notice_translator():
    """Render the Notice Translator workspace."""
    return render_template("notice_translator.html")

@app.route("/api/notice-translator/process", methods=["POST"])
def process_notice_api():
    """Extract text and detect language from a notice image."""

    uploaded_file = request.files.get("notice_image")

    if not uploaded_file:
        return jsonify({
            "success": False,
            "error": "Please upload a notice image."
        }), 400

    allowed_extensions = {"jpg", "jpeg", "png"}
    extension = uploaded_file.filename.rsplit(".", 1)[-1].lower()

    if extension not in allowed_extensions:
        return jsonify({
            "success": False,
            "error": "Only JPG, JPEG and PNG images are supported."
        }), 400

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=f".{extension}"
        ) as temp_file:
            uploaded_file.save(temp_file.name)
            temp_path = temp_file.name

        from modules.notice_translator import process_notice

        result = process_notice(temp_path)

        return jsonify(result), 200

    except Exception:
        logger.exception("Notice image processing failed")

        return jsonify({
            "success": False,
            "error": "Unable to process the notice image. Please try again."
        }), 500

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

@app.route("/api/notice-translator/translate", methods=["POST"])
def translate_notice_api():
    """Translate notice text and return structured sections."""

    data = request.get_json(silent=True) or {}

    source_text = data.get("text", "").strip()
    source_language = data.get("source_language", "").strip().lower()
    target_language = data.get("target_language", "").strip().lower()

    if not source_text:
        return jsonify({
            "success": False,
            "error": "No extracted text available for translation."
        }), 400

    try:
        from modules.notice_translator.translation import (
            translate_text,
            TranslationError
        )

        from modules.notice_translator.service import structure_notice_text

        # Step 1: Translate using MyMemory.
        translated_text = translate_text(
            source_text,
            source_language,
            target_language
        )

        if not isinstance(translated_text, str):
            raise ValueError("Translation returned an invalid response.")

        # Step 2: Organize translated text.
        structured_notice = structure_notice_text(translated_text)

        # Step 3: Return both original translation and structured output.
        return jsonify({
            "success": True,
            "translated_text": translated_text,
            "structured_notice": structured_notice,
            "source_language": source_language,
            "target_language": target_language,
            "message": "Notice translated and structured successfully."
        }), 200

    except ValueError as error:
        return jsonify({
            "success": False,
            "error": str(error)
        }), 400

    except TranslationError as error:
        return jsonify({
            "success": False,
            "error": str(error)
        }), 502

    except Exception:
        logger.exception("Notice translation and formatting failed.")

        return jsonify({
            "success": False,
            "error": "Unable to translate and structure this notice."
        }), 500


def process_notice_api():
    """Extract notice text and detect its language."""

    uploaded_file = request.files.get("notice_image")

    if not uploaded_file or not uploaded_file.filename:
        return jsonify({
            "success": False,
            "error": "Please upload a notice image."
        }), 400

    extension = Path(uploaded_file.filename).suffix.lower()

    if extension not in {".jpg", ".jpeg", ".png"}:
        return jsonify({
            "success": False,
            "error": "Only JPG, JPEG and PNG images are supported."
        }), 400

    if request.content_length and request.content_length > 11 * 1024 * 1024:
        return jsonify({
            "success": False,
            "error": "Image size must not exceed 10 MB."
        }), 413

    temp_path = None

    try:
        # Import only when the user requests image processing.
        from modules.notice_translator import process_notice

        with tempfile.NamedTemporaryFile(
            suffix=extension,
            delete=False
        ) as temp_file:
            temp_path = Path(temp_file.name)
            uploaded_file.save(temp_path)

        if temp_path.stat().st_size > 10 * 1024 * 1024:
            return jsonify({
                "success": False,
                "error": "Image size must not exceed 10 MB."
            }), 413

        result = process_notice(temp_path)

        return jsonify(result), 200

    except (ValueError, FileNotFoundError) as error:
        return jsonify({
            "success": False,
            "error": str(error)
        }), 400

    except Exception:
        logger.exception("Notice Translator processing failed")
        return jsonify({
            "success": False,
            "error": "Unable to process this image. Please try a clearer image."
        }), 500

    finally:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                logger.warning("Could not remove temporary notice image.")

# ==================================================
# 5. HEALTH API
# ==================================================

@app.route("/api/health", methods=["GET"])
def health():
    """Check Flask application and Ollama availability."""

    try:
        ollama_status = check_ollama_connection()

        return jsonify({
            "success": True,
            "application": "StudyMate AI",
            "status": "running",
            "ollama": ollama_status,
            "model": "qwen2.5:3b"
        }), 200

    except Exception as error:
        logger.exception("Health check failed")

        return jsonify({
            "success": False,
            "application": "StudyMate AI",
            "status": "running",
            "ollama": False,
            "error": str(error)
        }), 200


# ==================================================
# 6. AI CHAT API
# ==================================================

@app.route("/api/chat", methods=["POST"])
def chat():
    """Handle student queries through the Hybrid Supervisor."""

    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return create_error_response(
                "Invalid request. Please send JSON data."
            )

        message = data.get("message", "")

        if not isinstance(message, str):
            return create_error_response("Message must be text.")

        message = message.strip()

        if not message:
            return create_error_response("Please enter a message.")

        routing = route_student_query(message)

        if not isinstance(routing, dict):
            routing = {}

        intent = routing.get("intent", "unknown")

        routing_method = routing.get(
            "method",
            routing.get("routing_method", "unknown")
        )

        confidence = routing.get("confidence", 0.0)

        if not routing.get("success", False):
            logger.warning("Supervisor routing failed for query.")

            routing = {
                "success": True,
                "intent": "unknown",
                "agent": "general_assistant",
                "confidence": 0.0,
                "method": "fallback"
            }

            intent = "unknown"
            routing_method = "fallback"
            confidence = 0.0

        result = dispatch_student_query(message, routing)

        answer = result["answer"]
        selected_agent = result["agent"]

        logger.info(
            "Chat processed | Intent: %s | Agent: %s | Method: %s",
            intent,
            selected_agent,
            routing_method
        )

        return jsonify({
            "success": True,
            "user_message": message,
            "message": answer,
            "answer": answer,
            "intent": intent,
            "agent": selected_agent,
            "routing_method": routing_method,
            "confidence": confidence
        }), 200

    except Exception:
        logger.exception("Chat API error")

        return create_error_response(
            "Unable to process your message. "
            "Please check that Ollama is running.",
            500
        )


# ==================================================
# 7. QUICKNOTES DOCUMENT UPLOAD API
# ==================================================

@app.route("/api/quick-notes/upload", methods=["POST"])
def upload_quick_notes():
    """
    Upload PDF/TXT documents and generate study notes.

    Modes:
        quick: Python-based quick notes.
        detailed: Qwen-based detailed notes.
    """

    temporary_path = None

    try:
        if "file" not in request.files:
            return create_error_response("No document was uploaded.")

        uploaded_file = request.files["file"]

        if not uploaded_file.filename:
            return create_error_response("Please select a document.")

        original_filename = secure_filename(uploaded_file.filename)

        if not original_filename:
            return create_error_response("Invalid filename.")

        if not allowed_file(original_filename):
            return create_error_response(
                "Only PDF and TXT files are supported."
            )

        mode = request.form.get("mode", "quick").strip().lower()

        if mode not in ("quick", "detailed"):
            return create_error_response(
                "Invalid mode. Choose quick or detailed."
            )

        extension = Path(original_filename).suffix.lower()

        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=extension,
            prefix="studymate_",
            delete=False
        ) as temporary_file:

            uploaded_file.save(temporary_file)
            temporary_path = temporary_file.name

        file_size = get_uploaded_file_size(temporary_path)

        if file_size == 0:
            return create_error_response("The uploaded file is empty.")

        if file_size > MAX_FILE_SIZE:
            return create_error_response(
                "File size exceeds the 20 MB limit."
            )

        logger.info(
            "QuickNotes upload: %s | Mode: %s | Size: %s bytes",
            original_filename,
            mode,
            file_size
        )

        prepared = prepare_study_document(
            temporary_path,
            extract_diagrams=True
        )

        if not prepared.get("success"):
            raise RuntimeError("Document preparation failed.")

        document_text = prepared.get("text", "")

        if not document_text.strip():
            raise ValueError(
                "No readable text found in the document."
            )

        original_diagrams = prepared.get("original_diagrams", [])

        if mode == "quick":
            result = generate_quick_notes(
                document_text=document_text,
                filename=original_filename,
                original_diagrams=original_diagrams
            )
        else:
            result = generate_detailed_notes(
                document_text=document_text,
                filename=original_filename,
                original_diagrams=original_diagrams
            )

        if not isinstance(result, dict) or not result.get("success"):
            raise RuntimeError("Study notes generation failed.")

        notes = result.get("notes")

        if not isinstance(notes, str) or not notes.strip():
            raise RuntimeError("No study notes were generated.")

        response_data = {
            "success": True,
            "mode": mode,
            "filename": original_filename,
            "file_type": prepared.get("file_type"),
            "page_count": prepared.get("page_count", 0),
            "chunk_count": prepared.get("chunk_count", 0),
            "file_size": file_size,
            "model": result.get("model"),
            "processing_method": result.get("processing_method"),
            "sections_processed": result.get("sections_processed", 0),
            "source_characters": result.get(
                "source_characters",
                len(document_text)
            ),
            "selected_characters": result.get("selected_characters", 0),
            "notes": notes,
            "original_diagram_count": result.get(
                "original_diagram_count",
                0
            ),
            "generated_diagram_count": result.get(
                "generated_diagram_count",
                0
            ),
            "original_diagrams": result.get("original_diagrams", []),
            "generated_diagrams": result.get("generated_diagrams", [])
        }

        logger.info(
            "Notes generated successfully. Mode: %s",
            mode
        )

        return jsonify(response_data), 200

    except ValueError as error:
        logger.warning("QuickNotes validation error: %s", error)
        return create_error_response(str(error), 400)

    except Exception as error:
        logger.exception("QuickNotes processing failed")
        return create_error_response(str(error), 500)

    finally:
        if temporary_path and os.path.exists(temporary_path):
            try:
                os.remove(temporary_path)
            except OSError:
                logger.warning(
                    "Could not delete temporary file: %s",
                    temporary_path
                )


# ==================================================
# 8. BRAINCHECK - AI QUIZ GENERATION API
# ==================================================

@app.route("/api/brain-check/generate", methods=["POST"])
def generate_brain_check_quiz():
    """Generate MCQs using the local Qwen2.5:3B model."""

    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return create_error_response(
                "Invalid request. Please send JSON data."
            )

        subject = data.get("subject", "")
        topic = data.get("topic", "")
        difficulty = data.get("difficulty", "Medium")
        question_count = data.get("question_count", 5)

        if not isinstance(subject, str) or not subject.strip():
            return create_error_response("Please select a subject.")

        if not isinstance(topic, str) or not topic.strip():
            return create_error_response("Please enter a topic.")

        subject = subject.strip()
        topic = topic.strip()

        if len(subject) > 100 or len(topic) > 200:
            return create_error_response(
                "Subject or topic is too long."
            )

        if isinstance(question_count, bool):
            return create_error_response("Invalid question count.")

        try:
            question_count = int(question_count)
        except (ValueError, TypeError):
            return create_error_response("Invalid question count.")

        if question_count not in [5, 10, 15, 20]:
            return create_error_response(
                "Question count must be 5, 10, 15 or 20."
            )

        allowed_difficulties = ["Easy", "Medium", "Hard", "Mixed"]

        if not isinstance(difficulty, str):
            return create_error_response("Invalid difficulty.")

        difficulty = difficulty.strip()

        if difficulty not in allowed_difficulties:
            return create_error_response(
                "Please select a valid difficulty."
            )

        system_prompt = """
You are BrainCheck, an expert engineering education quiz generator.

STRICT RULES:
1. Generate exactly the requested number of questions.
2. Every question must have exactly four options: A, B, C and D.
3. Only one option must be correct.
4. The correct answer must be represented by its option letter.
5. Every question must have a clear explanation.
6. Avoid duplicate questions.
7. Match the requested subject, topic and difficulty.
8. Use technically accurate engineering-level concepts.
9. Do not include markdown formatting or code fences.

Return ONLY valid JSON in this structure:

{
    "title": "Quiz title",
    "questions": [
        {
            "question": "Question text",
            "options": {
                "A": "First option",
                "B": "Second option",
                "C": "Third option",
                "D": "Fourth option"
            },
            "correct_answer": "B",
            "explanation": "Explanation of the correct answer."
        }
    ]
}

Do not include text outside the JSON object.
"""

        user_prompt = f"""
Generate a quiz using these settings:

Subject: {subject}
Topic: {topic}
Difficulty: {difficulty}
Number of questions: {question_count}

Difficulty instructions:
- Easy: Basic concepts and definitions.
- Medium: Conceptual understanding and practical applications.
- Hard: Advanced concepts, problem-solving and analytical questions.
- Mixed: A combination of easy, medium and hard questions.

Generate exactly {question_count} unique MCQs.
Return only the JSON object.
"""

        logger.info(
            "Generating BrainCheck quiz | Subject: %s | Topic: %s | "
            "Difficulty: %s | Questions: %s",
            subject,
            topic,
            difficulty,
            question_count
        )

        max_tokens = min(6000, 500 + question_count * 250)

        ai_response = generate_response(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=max_tokens
        )

        if not isinstance(ai_response, str) or not ai_response.strip():
            raise ValueError("The AI returned an empty response.")

        cleaned_response = ai_response.strip()

        cleaned_response = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned_response,
            flags=re.IGNORECASE
        )

        cleaned_response = re.sub(
            r"\s*```$",
            "",
            cleaned_response
        )

        start_index = cleaned_response.find("{")
        end_index = cleaned_response.rfind("}")

        if start_index == -1 or end_index == -1:
            raise ValueError(
                "The AI did not return a valid JSON object."
            )

        json_text = cleaned_response[start_index:end_index + 1]
        quiz_data = json.loads(json_text)

        if not isinstance(quiz_data, dict):
            raise ValueError("The AI returned an invalid quiz structure.")

        questions = quiz_data.get("questions", [])

        if not isinstance(questions, list):
            raise ValueError("Invalid questions format.")

        if len(questions) != question_count:
            raise ValueError(
                f"AI generated {len(questions)} questions instead of "
                f"{question_count}. Please try generating again."
            )

        valid_keys = {"A", "B", "C", "D"}

        for index, question in enumerate(questions):

            if not isinstance(question, dict):
                raise ValueError(f"Question {index + 1} is invalid.")

            question_text = question.get("question")
            options = question.get("options")

            correct_answer = str(
                question.get("correct_answer", "")
            ).strip().upper()

            explanation = question.get("explanation")

            if (
                not isinstance(question_text, str)
                or not question_text.strip()
            ):
                raise ValueError(
                    f"Question {index + 1} is empty."
                )

            if not isinstance(options, dict):
                raise ValueError(
                    f"Options for question {index + 1} are invalid."
                )

            if set(options.keys()) != valid_keys:
                raise ValueError(
                    f"Question {index + 1} must have A, B, C and D options."
                )

            if correct_answer not in valid_keys:
                raise ValueError(
                    f"Correct answer for question {index + 1} is invalid."
                )

            for key in valid_keys:
                if (
                    not isinstance(options[key], str)
                    or not options[key].strip()
                ):
                    raise ValueError(
                        f"Option {key} in question {index + 1} is empty."
                    )

            if (
                not isinstance(explanation, str)
                or not explanation.strip()
            ):
                raise ValueError(
                    f"Explanation for question {index + 1} is missing."
                )

            question["correct_answer"] = correct_answer

        quiz_title = quiz_data.get("title", f"{topic} Quiz")

        if not isinstance(quiz_title, str) or not quiz_title.strip():
            quiz_title = f"{topic} Quiz"

        logger.info(
            "BrainCheck quiz generated successfully. Total questions: %s",
            len(questions)
        )

        return jsonify({
            "success": True,
            "title": quiz_title,
            "subject": subject,
            "topic": topic,
            "difficulty": difficulty,
            "total_questions": len(questions),
            "questions": questions
        }), 200

    except json.JSONDecodeError:
        logger.exception("BrainCheck returned invalid JSON.")

        return create_error_response(
            "The AI returned an invalid quiz format. "
            "Please try generating again.",
            500
        )

    except ValueError as error:
        logger.warning("BrainCheck validation error: %s", error)
        return create_error_response(str(error), 500)

    except Exception:
        logger.exception("BrainCheck quiz generation failed.")

        return create_error_response(
            "Quiz generation failed. Check that Ollama is running "
            "and try again.",
            500
        )


# ==================================================
# 9. BRAINCHECK - SAVE QUIZ RESULT TO MYSQL
# ==================================================

@app.route("/api/brain-check/save-result", methods=["POST"])
def save_brain_check_result():
    """Save a completed BrainCheck attempt in MySQL."""

    connection = None
    cursor = None

    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return create_error_response(
                "Invalid request. Please send JSON data."
            )

        subject = data.get("subject")
        topic = data.get("topic")
        difficulty = data.get("difficulty", "Medium")

        if not isinstance(subject, str) or not subject.strip():
            return create_error_response("Subject is required.")

        if not isinstance(topic, str) or not topic.strip():
            return create_error_response("Topic is required.")

        if not isinstance(difficulty, str) or not difficulty.strip():
            return create_error_response("Difficulty is required.")

        def read_non_negative_integer(field):
            value = data.get(field)

            if isinstance(value, bool):
                raise ValueError(
                    f"{field} must be a non-negative integer."
                )

            try:
                parsed = int(value)
            except (TypeError, ValueError):
                raise ValueError(
                    f"{field} must be a non-negative integer."
                )

            if parsed < 0 or str(value).strip() not in (
                str(parsed), f"{parsed}.0"
            ):
                raise ValueError(
                    f"{field} must be a non-negative integer."
                )

            return parsed

        total_questions = read_non_negative_integer("total_questions")
        correct_answers = read_non_negative_integer("correct_answers")
        incorrect_answers = read_non_negative_integer("incorrect_answers")
        unanswered = read_non_negative_integer("unanswered")

        if total_questions <= 0:
            return create_error_response(
                "total_questions must be greater than zero."
            )

        if (
            correct_answers + incorrect_answers + unanswered
            != total_questions
        ):
            return create_error_response(
                "Answer counts must add up to total_questions."
            )

        try:
            score_percentage = float(data.get("score_percentage"))
        except (TypeError, ValueError):
            return create_error_response(
                "score_percentage must be a valid number."
            )

        if not 0 <= score_percentage <= 100:
            return create_error_response(
                "score_percentage must be between 0 and 100."
            )

        connection = get_db_connection()

        if connection is None:
            return create_error_response(
                "Could not connect to the MySQL database.",
                503
            )

        cursor = connection.cursor()

        query = """
            INSERT INTO quiz_attempts (
                subject,
                topic,
                difficulty,
                total_questions,
                correct_answers,
                incorrect_answers,
                unanswered,
                score_percentage
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            subject.strip(),
            topic.strip(),
            difficulty.strip(),
            total_questions,
            correct_answers,
            incorrect_answers,
            unanswered,
            round(score_percentage, 2)
        )

        cursor.execute(query, values)
        connection.commit()

        attempt_id = cursor.lastrowid

        logger.info(
            "BrainCheck result saved | Attempt ID: %s | Topic: %s",
            attempt_id,
            topic.strip()
        )

        return jsonify({
            "success": True,
            "message": "Quiz result saved successfully.",
            "attempt_id": attempt_id
        }), 201

    except ValueError as error:
        return create_error_response(str(error), 400)

    except Exception:
        if connection and connection.is_connected():
            connection.rollback()

        logger.exception("Could not save BrainCheck result.")

        return create_error_response(
            "Unable to save quiz result. Please check the database.",
            500
        )

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# ==================================================
# 10. BRAINCHECK - RETRIEVE QUIZ HISTORY
# ==================================================

@app.route("/api/brain-check/history", methods=["GET"])
def get_brain_check_history():
    """Return the latest 20 BrainCheck attempts from MySQL."""

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            return create_error_response(
                "Could not connect to the MySQL database.",
                503
            )

        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id,
                subject,
                topic,
                difficulty,
                total_questions,
                correct_answers,
                incorrect_answers,
                unanswered,
                score_percentage,
                created_at
            FROM quiz_attempts
            ORDER BY created_at DESC, id DESC
            LIMIT 20
        """)

        attempts = cursor.fetchall()

        for attempt in attempts:
            if attempt.get("created_at"):
                attempt["created_at"] = attempt["created_at"].isoformat(
                    sep=" ",
                    timespec="seconds"
                )

            attempt["score_percentage"] = float(
                attempt["score_percentage"]
            )

        return jsonify({
            "success": True,
            "count": len(attempts),
            "history": attempts
        }), 200

    except Exception:
        logger.exception("Could not retrieve BrainCheck history.")

        return create_error_response(
            "Unable to retrieve quiz history. Please check the database.",
            500
        )

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# ==================================================
# 11. BRAINCHECK - AI PERSONALIZED STUDY PLAN
# ==================================================

@app.route("/api/brain-check/study-plan", methods=["GET"])
def generate_brain_check_study_plan():
    """Generate a personalized study plan from MySQL quiz history."""

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            return create_error_response(
                "Could not connect to the MySQL database.",
                503
            )

        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                topic,
                subject,
                AVG(score_percentage) AS average_score,
                COUNT(*) AS attempts
            FROM quiz_attempts
            GROUP BY topic, subject
            ORDER BY average_score ASC
        """)

        rows = cursor.fetchall()

        if not rows:
            return jsonify({
                "success": True,
                "topic_analysis": [],
                "study_plan": (
                    "Complete at least one BrainCheck quiz to receive "
                    "a personalized study plan."
                )
            }), 200

        topic_analysis = []

        for row in rows:
            average = round(float(row["average_score"]), 2)

            if average < 50:
                status = "Weak"
            elif average < 80:
                status = "Average"
            else:
                status = "Strong"

            topic_analysis.append({
                "topic": row["topic"],
                "subject": row["subject"],
                "average_score": average,
                "attempts": int(row["attempts"]),
                "status": status
            })

        # Release the database connection before calling the AI.
        cursor.close()
        cursor = None
        connection.close()
        connection = None

        user_prompt = f"""
Create a practical personalized study plan using this
student's actual BrainCheck performance data.

Performance data:
{json.dumps(topic_analysis, indent=2)}

Instructions:
- Prioritize topics with the lowest average scores.
- Explain what the student should revise.
- Suggest a practical weekly study routine.
- Include practice and revision activities.
- Also mention how to maintain strong topics.
- Use simple English.
- Do not invent performance scores.
- Make the plan achievable for an engineering student.

Return the plan in readable plain text with headings and bullet points.
"""

        system_prompt = """
You are StudyMate AI's personalized academic study planner.

Analyze the student's quiz performance and create
a realistic study plan.

Focus on weak topics first, then average topics.
Give actionable revision and practice suggestions.
Do not invent student performance information.
"""

        study_plan = generate_response(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=1400
        )

        if not isinstance(study_plan, str) or not study_plan.strip():
            raise RuntimeError("The AI returned an empty study plan.")

        return jsonify({
            "success": True,
            "topic_analysis": topic_analysis,
            "study_plan": study_plan.strip()
        }), 200

    except Exception:
        logger.exception("BrainCheck study plan generation failed.")

        return create_error_response(
            "Unable to generate the study plan. Check Ollama and MySQL.",
            500
        )

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# ==================================================
# 12. CAREER GUIDANCE - AI CAREER ANALYSIS API
# ==================================================

@app.route("/api/career-guidance/generate", methods=["POST"])
def generate_career_guidance():
    """
    Generate personalized career recommendations using Qwen2.5:3B.

    Returns:
        Career analysis
        Career recommendations
        Skill gap analysis
        Learning roadmap
        Placement tips
    """

    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return create_error_response(
                "Invalid request. Please send JSON data."
            )

        # ------------------------------------------
        # STEP 1: EXTRACT STUDENT INFORMATION
        # ------------------------------------------

        student_name = data.get("student_name", "")
        branch = data.get("branch", "")
        academic_year = data.get("academic_year", "")
        cgpa = data.get("cgpa")

        interests = data.get("interests", [])
        skills = data.get("skills", [])

        career_goal = data.get("career_goal", "")
        career_level = data.get("career_level", "")

        additional_information = data.get(
            "additional_information",
            ""
        )

        # ------------------------------------------
        # STEP 2: VALIDATE INPUT
        # ------------------------------------------

        if not isinstance(student_name, str) or not student_name.strip():
            return create_error_response("Student name is required.")

        if not isinstance(branch, str) or not branch.strip():
            return create_error_response("Engineering branch is required.")

        if not isinstance(academic_year, str) or not academic_year.strip():
            return create_error_response("Academic year is required.")

        if not isinstance(career_goal, str) or not career_goal.strip():
            return create_error_response("Career goal is required.")

        if not isinstance(interests, list) or not interests:
            return create_error_response(
                "Please provide your interests."
            )

        if not isinstance(skills, list) or not skills:
            return create_error_response(
                "Please provide your skills."
            )

        if (
            not all(isinstance(item, str) for item in interests)
            or not all(isinstance(item, str) for item in skills)
        ):
            return create_error_response(
                "Interest and skill values must be text."
            )

        if len(interests) > 20 or len(skills) > 30:
            return create_error_response(
                "Too many interests or skills were selected."
            )

        if cgpa is not None:
            if isinstance(cgpa, bool):
                return create_error_response("Invalid CGPA.")

            try:
                cgpa = float(cgpa)
            except (ValueError, TypeError):
                return create_error_response(
                    "CGPA must be a number."
                )

            if not 0 <= cgpa <= 10:
                return create_error_response(
                    "CGPA must be between 0 and 10."
                )

        if not isinstance(additional_information, str):
            return create_error_response(
                "Additional information must be text."
            )

        if len(student_name) > 100:
            return create_error_response("Student name is too long.")

        if len(additional_information) > 2000:
            return create_error_response(
                "Additional information is too long."
            )

        # ------------------------------------------
        # STEP 3: PREPARE STUDENT PROFILE
        # ------------------------------------------

        student_profile = {
            "Student Name": student_name.strip(),
            "Engineering Branch": branch.strip(),
            "Academic Year": academic_year.strip(),
            "CGPA": cgpa,
            "Interests": interests,
            "Existing Skills": skills,
            "Preferred Career": career_goal.strip(),
            "Career Preparation Level": (
                career_level if isinstance(career_level, str) else ""
            ),
            "Additional Information": additional_information.strip()
        }

        logger.info(
            "Career analysis requested | Branch: %s | Goal: %s",
            branch,
            career_goal
        )

        # ------------------------------------------
        # STEP 4: SYSTEM PROMPT
        # ------------------------------------------

        system_prompt = """
You are the Career Guidance Agent of StudyMate AI.

You are an expert career mentor for engineering students.

Your task is to analyze a student's academic profile,
interests, existing skills and career goals.

IMPORTANT INSTRUCTIONS:

1. Give realistic and personalized career guidance.
2. Consider the student's current academic year.
3. Do not assume the student knows skills not listed.
4. Identify relevant strengths.
5. Identify technical skills the student should develop.
6. Suggest suitable career paths.
7. Explain why each career is suitable.
8. Provide a practical learning roadmap.
9. Include internship and placement preparation advice.
10. Keep recommendations achievable for a student.
11. Do not guarantee jobs, salaries or placements.
12. Do not invent academic achievements.

Return ONLY valid JSON.

Use exactly this structure:

{
    "summary": "Personalized career analysis",

    "recommendations": [
        {
            "title": "Career title",
            "description": "Career explanation and why it matches the student",
            "suitability": "High"
        }
    ],

    "skill_gap_analysis": {
        "current_strengths": [
            "Existing skill or strength"
        ],
        "missing_skills": [
            "Skill that needs improvement"
        ],
        "recommended_skills": [
            "Skill recommended for the chosen career"
        ]
    },

    "learning_roadmap": [
        {
            "title": "Phase 1 - Fundamentals",
            "description": [
                "Learning task 1",
                "Learning task 2"
            ],
            "duration": "1-2 months"
        }
    ],

    "placement_tips": [
        "Practical placement preparation suggestion"
    ]
}

Do not include markdown code fences or text outside JSON.
"""

        # ------------------------------------------
        # STEP 5: USER PROMPT
        # ------------------------------------------

        user_prompt = f"""
Analyze the following student profile.

STUDENT PROFILE:

{json.dumps(student_profile, indent=4)}

Generate personalized career guidance based on this profile.

Include:
- At least 2 suitable career recommendations.
- Current strengths.
- Skills that need improvement.
- Recommended technical and soft skills.
- A step-by-step learning roadmap.
- Internship and placement preparation tips.

Make the roadmap suitable for the student's academic year.

Return only the requested JSON structure.
"""

        # ------------------------------------------
        # STEP 6: GENERATE USING QWEN
        # ------------------------------------------

        ai_response = generate_response(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=1200
        )

        if not isinstance(ai_response, str) or not ai_response.strip():
            raise ValueError(
                "The AI returned an empty career analysis."
            )

        # ------------------------------------------
        # STEP 7: CLEAN AI RESPONSE
        # ------------------------------------------

        cleaned_response = ai_response.strip()

        cleaned_response = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned_response,
            flags=re.IGNORECASE
        )

        cleaned_response = re.sub(
            r"\s*```$",
            "",
            cleaned_response
        )

        start_index = cleaned_response.find("{")
        end_index = cleaned_response.rfind("}")

        if start_index == -1 or end_index == -1:
            raise ValueError(
                "The AI did not return valid JSON."
            )

        json_text = cleaned_response[start_index:end_index + 1]
        career_data = json.loads(json_text)

        if not isinstance(career_data, dict):
            raise ValueError(
                "Invalid career analysis structure."
            )

        # ------------------------------------------
        # STEP 8: VALIDATE RESPONSE STRUCTURE
        # ------------------------------------------

        required_fields = [
            "summary",
            "recommendations",
            "skill_gap_analysis",
            "learning_roadmap",
            "placement_tips"
        ]

        for field in required_fields:
            if field not in career_data:
                raise ValueError(
                    f"AI response is missing the {field} section."
                )

        if not isinstance(career_data["recommendations"], list):
            raise ValueError("Invalid career recommendations.")

        if not isinstance(career_data["skill_gap_analysis"], dict):
            raise ValueError("Invalid skill gap analysis.")

        if not isinstance(career_data["learning_roadmap"], list):
            raise ValueError("Invalid learning roadmap.")

        if not isinstance(career_data["placement_tips"], list):
            raise ValueError("Invalid placement tips.")

        # ------------------------------------------
        # STEP 9: RETURN CAREER ANALYSIS
        # ------------------------------------------

        logger.info(
            "Career analysis generated successfully for %s.",
            student_name
        )

        return jsonify({
            "success": True,
            "student_name": student_name,
            "summary": career_data["summary"],
            "recommendations": career_data["recommendations"],
            "skill_gap_analysis": career_data["skill_gap_analysis"],
            "learning_roadmap": career_data["learning_roadmap"],
            "placement_tips": career_data["placement_tips"]
        }), 200

    except json.JSONDecodeError:
        logger.exception(
            "Career Guidance returned invalid JSON."
        )

        return create_error_response(
            "The AI returned an invalid response. Please try again.",
            500
        )

    except ValueError as error:
        logger.warning(
            "Career Guidance validation error: %s",
            error
        )

        return create_error_response(str(error), 500)

    except Exception:
        logger.exception("Career Guidance generation failed.")

        return create_error_response(
            "Career analysis failed. Check that Ollama is running.",
            500
        )


# ==================================================
# 13. ASKAWAY - DOCUMENT CHATBOT APIs
# ==================================================

def get_ask_away_session_id():
    """Return a browser-session-specific AskAway document key."""

    if "ask_away_session_id" not in session:
        session["ask_away_session_id"] = uuid.uuid4().hex

    return session["ask_away_session_id"]


@app.route("/api/ask-away/upload", methods=["POST"])
def ask_away_upload():
    """Upload and index a PDF/TXT document for the current session."""

    temporary_path = None

    try:
        if "file" not in request.files:
            return create_error_response("No document was uploaded.")

        uploaded_file = request.files["file"]

        if not uploaded_file.filename:
            return create_error_response("Please select a document.")

        original_filename = secure_filename(uploaded_file.filename)

        if not original_filename or not allowed_file(original_filename):
            return create_error_response(
                "Only PDF and TXT files are supported."
            )

        extension = Path(original_filename).suffix.lower()

        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=extension,
            prefix="askaway_",
            delete=False
        ) as temporary_file:
            uploaded_file.save(temporary_file)
            temporary_path = temporary_file.name

        file_size = get_uploaded_file_size(temporary_path)

        if file_size == 0:
            return create_error_response("The uploaded file is empty.")

        if file_size > MAX_FILE_SIZE:
            return create_error_response(
                "File size exceeds the 20 MB limit."
            )

        session_id = get_ask_away_session_id()
        result = upload_document(
            file_path=temporary_path,
            session_id=session_id
        )

        # Return the user's original filename rather than the temporary name.
        result["filename"] = original_filename

        logger.info(
            "AskAway document processed | Filename: %s | Size: %s bytes",
            original_filename,
            file_size
        )

        return jsonify(result), 200

    except ValueError as error:
        logger.warning("AskAway upload validation error: %s", error)
        return create_error_response(str(error), 400)

    except Exception:
        logger.exception("AskAway document upload failed.")
        return create_error_response(
            "Unable to process the document. Please check the file and try again.",
            500
        )

    finally:
        if temporary_path and os.path.exists(temporary_path):
            try:
                os.remove(temporary_path)
            except OSError:
                logger.warning(
                    "Could not delete AskAway temporary file: %s",
                    temporary_path
                )


@app.route("/api/ask-away/ask", methods=["POST"])
def ask_away_question():
    """Answer a question using the current session's uploaded document."""

    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return create_error_response(
                "Invalid request. Please send JSON data."
            )

        question = data.get("question", "")

        if not isinstance(question, str) or not question.strip():
            return create_error_response("Please enter a question.")

        if len(question) > 2000:
            return create_error_response("Question is too long.")

        result = ask_question(
            question=question.strip(),
            session_id=get_ask_away_session_id()
        )

        return jsonify(result), 200

    except ValueError as error:
        return create_error_response(str(error), 400)

    except Exception:
        logger.exception("AskAway question processing failed.")
        return create_error_response(
            "Unable to answer the question. Please check that Ollama is running.",
            500
        )


@app.route("/api/ask-away/document", methods=["GET"])
def ask_away_document_info():
    """Return information about the current session's document."""

    result = get_document_info(get_ask_away_session_id())
    return jsonify(result), 200


@app.route("/api/ask-away/reset", methods=["POST"])
def ask_away_reset():
    """Clear the current session's AskAway document."""

    result = clear_document(get_ask_away_session_id())
    return jsonify(result), 200


# ==================================================
# 15. SENTIMENT ANALYSIS API (CO2)
# ==================================================

@app.route("/api/sentiment/analyze", methods=["POST"])
def analyze_sentiment_api():
    """
    Analyze the sentiment of input text using VADER.

    CO2: Implementation and evaluation of sentiment analysis.
    """

    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return create_error_response(
                "Invalid request. Please send JSON data."
            )

        text = data.get("text", "")

        if not isinstance(text, str) or not text.strip():
            return create_error_response("Please provide text to analyze.")

        if len(text) > 10000:
            return create_error_response("Text is too long (max 10000 characters).")

        mode = data.get("mode", "overall").strip().lower()

        from nlp.sentiment import analyze_sentiment, analyze_sentences

        if mode == "sentences":
            result = analyze_sentences(text.strip())
        else:
            result = analyze_sentiment(text.strip())

        return jsonify({
            "success": True,
            "mode": mode,
            **result,
        }), 200

    except ValueError as error:
        return create_error_response(str(error), 400)

    except Exception:
        logger.exception("Sentiment analysis failed.")
        return create_error_response(
            "Sentiment analysis failed. Please try again.",
            500,
        )


@app.route("/api/sentiment/batch", methods=["POST"])
def batch_sentiment_api():
    """Analyze sentiment for multiple text inputs."""

    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return create_error_response(
                "Invalid request. Please send JSON data."
            )

        texts = data.get("texts", [])

        if not isinstance(texts, list) or not texts:
            return create_error_response(
                "Please provide a non-empty list of texts."
            )

        if len(texts) > 100:
            return create_error_response("Maximum 100 texts allowed per batch.")

        from nlp.sentiment import analyze_batch

        result = analyze_batch(texts)

        return jsonify({
            "success": True,
            **result,
        }), 200

    except ValueError as error:
        return create_error_response(str(error), 400)

    except Exception:
        logger.exception("Batch sentiment analysis failed.")
        return create_error_response(
            "Batch sentiment analysis failed. Please try again.",
            500,
        )


# ==================================================
# 16. SENTIMENT EVALUATION API (CO2)
# ==================================================

@app.route("/api/sentiment/evaluate", methods=["GET"])
def evaluate_sentiment_api():
    """
    Evaluate the sentiment analysis model using built-in test data.

    CO2: Evaluation of sentiment analysis using appropriate metrics.

    Returns accuracy, precision, recall, F1-score and confusion matrix.
    """

    try:
        from nlp.evaluation import run_default_evaluation

        result = run_default_evaluation()

        return jsonify({
            "success": True,
            **result,
        }), 200

    except Exception:
        logger.exception("Sentiment evaluation failed.")
        return create_error_response(
            "Sentiment model evaluation failed. Please try again.",
            500,
        )


@app.route("/api/sentiment/evaluate/custom", methods=["POST"])
def evaluate_sentiment_custom_api():
    """
    Evaluate sentiment analysis against user-provided test data.

    Expects JSON: {"test_data": [{"text": "...", "expected": "Positive"}, ...]}
    """

    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return create_error_response(
                "Invalid request. Please send JSON data."
            )

        test_data = data.get("test_data", [])

        if not isinstance(test_data, list) or not test_data:
            return create_error_response(
                "Please provide test_data as a non-empty list."
            )

        if len(test_data) > 500:
            return create_error_response("Maximum 500 test samples allowed.")

        from nlp.evaluation import evaluate_sentiment_model

        result = evaluate_sentiment_model(test_data)

        return jsonify({
            "success": True,
            **result,
        }), 200

    except ValueError as error:
        return create_error_response(str(error), 400)

    except Exception:
        logger.exception("Custom sentiment evaluation failed.")
        return create_error_response(
            "Custom sentiment evaluation failed.",
            500,
        )


# ==================================================
# 17. TOPIC MODELING API (CO3)
# ==================================================

@app.route("/api/topic-modeling/extract", methods=["POST"])
def extract_topics_api():
    """
    Extract topics from uploaded text using LDA.

    CO3: Implementation of topic modeling using appropriate
         NLP techniques.
    """

    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return create_error_response(
                "Invalid request. Please send JSON data."
            )

        text = data.get("text", "")

        if not isinstance(text, str) or not text.strip():
            return create_error_response(
                "Please provide text for topic modeling."
            )

        if len(text) < 200:
            return create_error_response(
                "Text is too short for topic modeling. "
                "Please provide at least 200 characters."
            )

        if len(text) > 100000:
            return create_error_response(
                "Text is too long (max 100000 characters)."
            )

        num_topics = data.get("num_topics", 5)

        try:
            num_topics = int(num_topics)
        except (ValueError, TypeError):
            num_topics = 5

        num_topics = max(2, min(num_topics, 15))

        from nlp.topic_modeling import extract_topics_from_text

        result = extract_topics_from_text(
            text=text.strip(),
            num_topics=num_topics,
        )

        logger.info(
            "Topic modeling completed | Topics: %d",
            result.get("num_topics", 0),
        )

        return jsonify(result), 200

    except ValueError as error:
        return create_error_response(str(error), 400)

    except Exception:
        logger.exception("Topic modeling failed.")
        return create_error_response(
            "Topic modeling failed. Please provide more text content.",
            500,
        )


@app.route("/api/topic-modeling/keywords", methods=["POST"])
def extract_keywords_api():
    """
    Extract top TF-IDF keywords from input text.

    CO3: NLP techniques for text analysis.
    """

    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return create_error_response(
                "Invalid request. Please send JSON data."
            )

        text = data.get("text", "")

        if not isinstance(text, str) or not text.strip():
            return create_error_response("Please provide text for analysis.")

        if len(text) < 50:
            return create_error_response(
                "Text is too short. Provide at least 50 characters."
            )

        top_n = data.get("top_n", 20)

        try:
            top_n = int(top_n)
        except (ValueError, TypeError):
            top_n = 20

        top_n = max(5, min(top_n, 50))

        from nlp.topic_modeling import (
            extract_tfidf_keywords,
            split_into_segments,
        )

        segments = split_into_segments(text.strip(), segment_size=500)

        if len(segments) < 1:
            segments = [text.strip()]

        result = extract_tfidf_keywords(
            documents=segments,
            top_n=top_n,
        )

        return jsonify(result), 200

    except ValueError as error:
        return create_error_response(str(error), 400)

    except Exception:
        logger.exception("TF-IDF keyword extraction failed.")
        return create_error_response(
            "Keyword extraction failed. Please try again.",
            500,
        )


# ==================================================
# 18. ERROR HANDLERS
# ==================================================

@app.errorhandler(413)
def file_too_large(error):
    return create_error_response(
        "File is too large. VoiceSnap allows up to 100 MB; document tools allow 20 MB.",
        413
    )


@app.errorhandler(404)
def page_not_found(error):
    return create_error_response(
        "Requested page or API endpoint was not found.",
        404
    )


@app.errorhandler(500)
def internal_server_error(error):
    logger.error("Internal server error: %s", error)

    return create_error_response(
        "An internal server error occurred.",
        500
    )


# ==================================================
# 19. RUN APPLICATION
# ==================================================

if __name__ == "__main__":

    print("\n")
    print("=" * 52)
    print("             STUDYMATE AI SERVER")
    print("=" * 52)

    print("Application      : http://127.0.0.1:5000")
    print("Dashboard        : http://127.0.0.1:5000/")
    print("Assistant        : http://127.0.0.1:5000/assistant")
    print("QuickNotes       : http://127.0.0.1:5000/quick-notes")
    print("BrainCheck       : http://127.0.0.1:5000/brain-check")
    print("Career Guidance  : http://127.0.0.1:5000/career-guidance")
    print("AskAway          : http://127.0.0.1:5000/ask-away")
    print("VoiceSnap        : http://127.0.0.1:5000/voice-snap")
    print("Health API       : http://127.0.0.1:5000/api/health")

    print("-" * 52)
    print("Sentiment API    : POST /api/sentiment/analyze")
    print("Sentiment Eval   : GET  /api/sentiment/evaluate")
    print("Topic Modeling   : POST /api/topic-modeling/extract")
    print("TF-IDF Keywords  : POST /api/topic-modeling/keywords")

    print("=" * 52)
    print("\n")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
