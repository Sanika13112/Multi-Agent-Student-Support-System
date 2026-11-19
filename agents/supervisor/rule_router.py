
"""
Multi-Agent Student Support System

Rule-Based Intent Router

Identifies student queries using predefined
keywords and phrase matching.

This is Stage 1 of the Hybrid Supervisor Agent.
"""

import re


# =========================================
# 1. SUPPORTED INTENT CATEGORIES
# =========================================

INTENT_KEYWORDS = {

    "study_explanation": [
        "explain",
        "definition",
        "define",
        "what is",
        "what are",
        "how does",
        "how do",
        "describe",
        "difference between",
        "concept of",
        "meaning of",
        "teach me",
        "help me understand",
        "working of"
    ],

    "career_guidance": [
        "career",
        "roadmap",
        "job",
        "career path",
        "which field",
        "skills required",
        "placement",
        "career options",
        "learning path",
        "become a",
        "future scope",
        "professional growth"
    ],

    "interview_preparation": [
        "interview",
        "technical round",
        "hr round",
        "interview questions",
        "mock interview",
        "placement questions",
        "technical questions",
        "interview preparation"
    ],

    "greeting": [
        "hello",
        "hi",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",
        "how are you"
    ],

    "voice_snap": [
        "voice notes",
        "audio notes",
        "transcribe audio",
        "convert audio",
        "speech to text",
        "audio transcription",
        "lecture recording",
        "convert recording"
    ],

    "quick_notes": [
        "summarize pdf",
        "generate notes",
        "make notes",
        "create summary",
        "extract key points",
        "quick notes",
        "study notes",
        "summarize document",
        "important points from pdf"
    ],

    "ask_away": [
        "ask my document",
        "ask pdf",
        "question from document",
        "document question",
        "ask my pdf",
        "chat with pdf",
        "chat with document",
        "questions about my document"
    ],

    "brain_check": [
        "generate quiz",
        "create mcq",
        "practice questions",
        "test my knowledge",
        "generate assessment",
        "take a quiz",
        "create quiz",
        "multiple choice questions",
        "test me",
        "quiz me"
    ]
}


# =========================================
# 2. NORMALIZE USER MESSAGE
# =========================================

def normalize_message(message):
    """
    Normalize the message for consistent matching.
    """

    message = message.lower().strip()

    # Replace repeated whitespace with a single space.
    message = re.sub(r"\s+", " ", message)

    return message


# =========================================
# 3. CHECK KEYWORD MATCHING
# =========================================

def contains_keyword(message, keyword):
    """
    Check whether a keyword or phrase exists
    as a complete word or phrase.

    Prevents accidental substring matches.
    """

    pattern = (
        r"(?<!\w)"
        + re.escape(keyword.lower())
        + r"(?!\w)"
    )

    return re.search(pattern, message) is not None


# =========================================
# 4. EXACT GREETING DETECTION
# =========================================

def is_greeting(message):
    """
    Identify simple greeting messages.
    """

    greetings = {
        "hi",
        "hello",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",
        "how are you"
    }

    cleaned_message = message.strip(" !?.,")

    return cleaned_message in greetings


# =========================================
# 5. RULE-BASED ROUTER
# =========================================

def rule_based_router(message):
    """
    Identify student intent using predefined rules.

    Args:
        message (str): Student's input query.

    Returns:
        dict: Detected intent and routing information.

    Supported agents:
        study_explanation
        career_guidance
        interview_preparation
        greeting
        voice_snap
        quick_notes
        ask_away
        brain_check
    """

    # -------------------------------------
    # STEP 1: VALIDATE INPUT
    # -------------------------------------

    if not isinstance(message, str) or not message.strip():

        return {
            "intent": "unknown",
            "confidence": 0.0,
            "agent": None,
            "method": "rule_based"
        }

    # -------------------------------------
    # STEP 2: NORMALIZE MESSAGE
    # -------------------------------------

    text = normalize_message(message)

    # -------------------------------------
    # STEP 3: CHECK GREETING
    # -------------------------------------

    if is_greeting(text):

        return {
            "intent": "greeting",
            "confidence": 1.0,
            "agent": "greeting",
            "method": "rule_based"
        }

    # -------------------------------------
    # STEP 4: CHECK INTENT KEYWORDS
    # -------------------------------------

    # Collect all matching intents.
    matches = []

    for intent, keywords in INTENT_KEYWORDS.items():

        if intent == "greeting":
            continue

        matched_keywords = [
            keyword
            for keyword in keywords
            if contains_keyword(text, keyword)
        ]

        if matched_keywords:

            # Prefer the longest matching phrase.
            longest_match = max(
                matched_keywords,
                key=len
            )

            matches.append({
                "intent": intent,
                "keyword": longest_match,
                "keyword_length": len(longest_match)
            })

    # -------------------------------------
    # STEP 5: SELECT BEST MATCH
    # -------------------------------------

    if matches:

        # Select the intent with the longest matching phrase.
        best_match = max(
            matches,
            key=lambda item: item["keyword_length"]
        )

        detected_intent = best_match["intent"]

        return {
            "intent": detected_intent,
            "confidence": 1.0,
            "agent": detected_intent,
            "method": "rule_based"
        }

    # -------------------------------------
    # STEP 6: UNKNOWN INTENT
    # -------------------------------------

    return {
        "intent": "unknown",
        "confidence": 0.0,
        "agent": None,
        "method": "rule_based"
    }
