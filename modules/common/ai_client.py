
"""
Multi-Agent Student Support System

Optimized Ollama AI Client

Connects Python with the locally running
Qwen2.5:1.5B language model.
"""

import math
import ollama


# =========================================
# 1. MODEL CONFIGURATION
# =========================================

MODEL_NAME = "qwen2.5:1.5b"

# Keep the model loaded for 10 minutes.
MODEL_KEEP_ALIVE = "10m"


# =========================================
# 2. AI RESPONSE GENERATION
# =========================================

def generate_response(
    prompt,
    system_prompt=None,
    temperature=0.7,
    max_tokens=None
):
    """
    Generate an AI response using local Ollama.

    Parameters:
        prompt (str): User's question or instruction.
        system_prompt (str): Optional system instructions.
        temperature (float): Controls response creativity.
        max_tokens (int): Maximum generated tokens.

    Returns:
        str: AI-generated response.

    Raises:
        ValueError: If input values are invalid.
        RuntimeError: If Ollama generation fails.
    """

    # =====================================
    # STEP 1: VALIDATE USER PROMPT
    # =====================================

    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    # =====================================
    # STEP 2: VALIDATE SYSTEM PROMPT
    # =====================================

    if system_prompt is not None and not isinstance(system_prompt, str):
        raise TypeError("System prompt must be a string.")

    # =====================================
    # STEP 3: VALIDATE TEMPERATURE
    # =====================================

    if (
        isinstance(temperature, bool)
        or not isinstance(temperature, (int, float))
    ):
        raise TypeError("Temperature must be a number.")

    if not math.isfinite(temperature) or not 0 <= temperature <= 2:
        raise ValueError("Temperature must be between 0 and 2.")

    # =====================================
    # STEP 4: VALIDATE MAX TOKENS
    # =====================================

    if max_tokens is not None:

        if (
            isinstance(max_tokens, bool)
            or not isinstance(max_tokens, int)
            or max_tokens <= 0
        ):
            raise ValueError("max_tokens must be a positive integer.")

    # =====================================
    # STEP 5: PREPARE CHAT MESSAGES
    # =====================================

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

    # =====================================
    # STEP 6: GENERATION OPTIONS
    # =====================================

    options = {
        "temperature": temperature,
        "num_ctx": 4096
    }

    if max_tokens is not None:
        options["num_predict"] = max_tokens

    # =====================================
    # STEP 7: GENERATE AI RESPONSE
    # =====================================

    try:

        response = ollama.chat(
            model=MODEL_NAME,
            messages=messages,
            options=options,
            keep_alive=MODEL_KEEP_ALIVE
        )

        answer = response["message"]["content"]

        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("The AI model returned an empty response.")

        return answer.strip()

    except ollama.ResponseError as error:

        raise RuntimeError(
            f"Ollama model error: {error.error}"
        ) from error

    except Exception as error:

        raise RuntimeError(
            "Unable to generate AI response. "
            "Make sure Ollama is running and "
            f"{MODEL_NAME} is installed. Details: {error}"
        ) from error


# =========================================
# 3. CHECK OLLAMA CONNECTION
# =========================================

def check_ollama_connection():
    """
    Check whether Ollama is running
    and the required model is available.

    Returns:
        bool: True if the model is available,
              otherwise False.
    """

    try:

        models = ollama.list()

        available_models = []

        for model in models.models:

            model_name = model.model

            if model_name:
                available_models.append(model_name)

        return any(
            name == MODEL_NAME
            or name.startswith(MODEL_NAME + ":")
            for name in available_models
        )

    except Exception:

        return False
