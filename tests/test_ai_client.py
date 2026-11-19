
from modules.common.ai_client import (
    generate_response,
    check_ollama_connection
)


def main():

    print("Checking Ollama connection...")

    if not check_ollama_connection():
        print("Ollama model is unavailable.")
        return

    print("Ollama connection successful!")

    print("\nGenerating AI response...")

    answer = generate_response(
        prompt="Explain Machine Learning in simple words "
               "with one engineering example.",
        system_prompt="You are a helpful B.Tech engineering tutor."
    )

    print("\nAI Response:")
    print(answer)


if __name__ == "__main__":
    main()
