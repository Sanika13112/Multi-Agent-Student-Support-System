
"""
Multi-Agent Student Support System
Dual-provider AI Client

Local: Ollama + Qwen2.5
Cloud: Groq API
"""

import os
import math
import ollama
from groq import Groq


# =========================================
# 1. PROVIDER CONFIGURATION
# =========================================

AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama").lower()

OLLAMA_MODEL = "qwen2.5:1.5b"
OLLAMA_KEEP_ALIVE = "10m"

GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")


# =========================================
# 2. OLLAMA RESPONSE
# =========================================

def generate_ollama_response(
    messages,
    temperature,
    max_tokens,
    json_mode
):
    options = {
        "temperature": temperature,
        "num_ctx": 4096
    }

    if max_tokens is not None:
        options["num_predict"] = max_tokens

    extra_arguments = {"format": "json"} if json_mode else {}

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=messages,
        options=options,
        keep_alive=OLLAMA_KEEP_ALIVE,
        **extra_arguments
    )

    answer = response["message"]["content"]

    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError("Ollama returned an empty response.")

    return answer.strip()


# =========================================
# 3. GROQ RESPONSE
# =========================================

def generate_groq_response(
    messages,
    temperature,
    max_tokens,
    json_mode
):
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing from environment variables."
        )

    client = Groq(api_key=api_key)

    arguments = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_completion_tokens": max_tokens or 1200,
"reasoning_effort": "low"
    }

    if json_mode:
        arguments["response_format"] = {
            "type": "json_object"
        }

    response = client.chat.completions.create(**arguments)

    answer = response.choices[0].message.content

    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError("Groq returned an empty response.")

    return answer.strip()


# =========================================
# 4. MAIN AI RESPONSE GENERATION
# =========================================

def generate_response(
    prompt,
    system_prompt=None,
    temperature=0.7,
    max_tokens=None,
    json_mode=False
):
    """Generate responses using Ollama locally or Groq in the cloud."""

    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    if system_prompt is not None and not isinstance(
        system_prompt, str
    ):
        raise TypeError("System prompt must be a string.")

    if (
        isinstance(temperature, bool)
        or not isinstance(temperature, (int, float))
    ):
        raise TypeError("Temperature must be a number.")

    if not math.isfinite(temperature) or not 0 <= temperature <= 2:
        raise ValueError("Temperature must be between 0 and 2.")

    if max_tokens is not None:
        if (
            isinstance(max_tokens, bool)
            or not isinstance(max_tokens, int)
            or max_tokens <= 0
        ):
            raise ValueError(
                "max_tokens must be a positive integer."
            )

    messages = []

    if system_prompt and system_prompt.strip():
        messages.append({
            "role": "system",
            "content": system_prompt.strip()
        })

    messages.append({
        "role": "user",
        "content": prompt.strip()
    })

    try:
        if AI_PROVIDER == "ollama":
            return generate_ollama_response(
                messages,
                temperature,
                max_tokens,
                json_mode
            )

        elif AI_PROVIDER == "groq":
            return generate_groq_response(
                messages,
                temperature,
                max_tokens,
                json_mode
            )

        else:
            raise ValueError(
                f"Unsupported AI_PROVIDER: {AI_PROVIDER}"
            )

    except Exception as error:
        raise RuntimeError(
            f"AI response generation failed using "
            f"{AI_PROVIDER}: {error}"
        ) from error


# =========================================
# 5. CONNECTION CHECK
# =========================================

def check_ollama_connection():
    """Check whether the local Ollama model is available."""

    if AI_PROVIDER != "ollama":
        return False

    try:
        models = ollama.list()

        available_models = [
            model.model
            for model in models.models
            if model.model
        ]

        return any(
            name == OLLAMA_MODEL
            or name.startswith(OLLAMA_MODEL + ":")
            for name in available_models
        )

    except Exception as error:
        print(f"Ollama connection error: {error}")
        return False


def check_ai_connection():
    """Check whether the configured AI provider is configured."""

    if AI_PROVIDER == "ollama":
        return check_ollama_connection()

    if AI_PROVIDER == "groq":
        return bool(os.getenv("GROQ_API_KEY"))

    return False
