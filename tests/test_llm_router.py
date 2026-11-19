
from agents.supervisor.llm_router import llm_based_router


def main():

    test_queries = [
        "I am confused about which career path to choose.",
        "How can I become a successful AI engineer?",
        "I have an important technical round next week.",
        "Can you check my understanding through a quiz?",
        "I want to convert my lecture recording into notes."
    ]

    print("\n===== LLM ROUTER TEST =====\n")

    for query in test_queries:

        print("Student Query:", query)

        result = llm_based_router(query)

        print("Detected Intent:", result["intent"])
        print("Confidence:", result["confidence"])
        print("Selected Agent:", result["agent"])
        print("Method:", result["method"])

        print("-" * 60)


if __name__ == "__main__":
    main()
