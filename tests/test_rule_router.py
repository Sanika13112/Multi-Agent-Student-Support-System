
"""
Tests for the Rule-Based Supervisor Router.
"""

from agents.supervisor.rule_router import rule_based_router


def main():

    test_queries = [
        "Explain machine learning",
        "I want a career roadmap",
        "Give me interview questions",
        "Hello, how are you?",
        "Convert audio into text",
        "Generate notes from my PDF",
        "Ask a question from my document",
        "Generate a quiz for me",
        "Tell me something interesting"
    ]

    print("\n===== RULE-BASED ROUTER TEST =====\n")

    for query in test_queries:

        result = rule_based_router(query)

        print("Student Query:", query)
        print("Detected Intent:", result["intent"])
        print("Selected Agent:", result["agent"])
        print("Routing Method:", result["method"])
        print("-" * 50)


if __name__ == "__main__":
    main()
