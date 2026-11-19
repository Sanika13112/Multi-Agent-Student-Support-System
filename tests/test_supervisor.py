
from agents.supervisor.supervisor import route_student_query


def main():

    test_queries = [
        "Explain machine learning",
        "I am confused about choosing my career.",
        "Give me technical interview questions.",
        "Hello, how are you?",
        "I want to convert my lecture recording into notes.",
        "Can you test my knowledge with a quiz?",
        "Tell me something interesting."
    ]

    print("\n===== HYBRID SUPERVISOR TEST =====\n")

    for query in test_queries:

        print("Student Query:", query)

        result = route_student_query(query)

        print("Intent:", result["intent"])
        print("Selected Agent:", result["agent"])
        print("Routing Method:", result["method"])
        print("Confidence:", result["confidence"])

        print("-" * 60)


if __name__ == "__main__":
    main()

