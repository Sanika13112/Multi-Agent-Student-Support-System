
"""
QuickNotes - Improved Generated Diagram Engine

Creates Mermaid flowcharts and concept maps using Python rules.
No AI model required.

Supported topics:
- Complexity Classes
- Polynomial-Time Reduction
- SAT and 3-SAT
- Approximation Algorithms
- Greedy Algorithms
- Dynamic Programming
- Divide and Conquer
- Branch and Bound
- Backtracking
- Time and Space Complexity
"""

import re


# --------------------------------------------------
# MERMAID LABEL CLEANING
# --------------------------------------------------

def clean_label(text, max_length=100):
    """Make text safer for Mermaid diagram labels."""

    text = str(text).strip()

    # Replace characters that can interfere with Mermaid syntax
    text = text.replace('"', "'")
    text = text.replace("[", "(").replace("]", ")")
    text = text.replace("{", "(").replace("}", ")")
    text = text.replace("|", "/")

    # Remove unnecessary whitespace
    text = re.sub(r"\s+", " ", text)

    if len(text) > max_length:
        text = text[:max_length - 3] + "..."

    return text


# --------------------------------------------------
# FLOWCHART GENERATOR
# --------------------------------------------------

def create_flowchart(title, steps):
    """Create a Mermaid flowchart from sequential steps."""

    title = clean_label(title)
    steps = [
        clean_label(step)
        for step in steps
        if str(step).strip()
    ]

    lines = [
        "flowchart TD",
        f'START(["{title} - Start"])'
    ]

    previous = "START"

    for index, step in enumerate(steps, start=1):
        node = f"STEP{index}"

        lines.append(f'{node}["{step}"]')
        lines.append(f"{previous} --> {node}")

        previous = node

    lines.append(f'{previous} --> END(["End"])')

    return {
        "title": title,
        "type": "flowchart",
        "mermaid": "\n".join(lines)
    }


# --------------------------------------------------
# DECISION FLOWCHART GENERATOR
# --------------------------------------------------

def create_decision_flowchart(title, steps, decision, yes_result, no_result):
    """Create a flowchart containing a decision node."""

    title = clean_label(title)
    decision = clean_label(decision)
    yes_result = clean_label(yes_result)
    no_result = clean_label(no_result)

    lines = [
        "flowchart TD",
        f'START(["{title} - Start"])'
    ]

    previous = "START"

    for index, step in enumerate(steps, start=1):
        node = f"STEP{index}"
        label = clean_label(step)

        lines.append(f'{node}["{label}"]')
        lines.append(f"{previous} --> {node}")

        previous = node

    lines.extend([
        f'DECISION{{"{decision}"}}',
        f"{previous} --> DECISION",
        f'YES["{yes_result}"]',
        f'NO["{no_result}"]',
        "DECISION -->|Yes| YES",
        "DECISION -->|No| NO",
        "YES --> END([End])",
        "NO --> END"
    ])

    return {
        "title": title,
        "type": "flowchart",
        "mermaid": "\n".join(lines)
    }


# --------------------------------------------------
# CONCEPT MAP GENERATOR
# --------------------------------------------------

def create_concept_map(title, concepts):
    """Create a concept map with connected concepts."""

    title = clean_label(title)

    lines = [
        "flowchart TD",
        f'MAIN["{title}"]'
    ]

    for index, concept in enumerate(concepts, start=1):

        if isinstance(concept, (tuple, list)) and len(concept) == 2:
            parent, child = concept

            parent_id = f"PARENT{index}"
            child_id = f"CHILD{index}"

            lines.append(
                f'{parent_id}["{clean_label(parent)}"]'
            )
            lines.append(
                f'{child_id}["{clean_label(child)}"]'
            )

            lines.append(f"MAIN --> {parent_id}")
            lines.append(f"{parent_id} --> {child_id}")

        else:
            node = f"CONCEPT{index}"
            label = clean_label(concept)

            lines.append(f'{node}["{label}"]')
            lines.append(f"MAIN --> {node}")

    return {
        "title": title,
        "type": "concept_map",
        "mermaid": "\n".join(lines)
    }


# --------------------------------------------------
# TOPIC DIAGRAM TEMPLATES
# --------------------------------------------------

def generate_diagrams(document_text):
    """
    Detect supported topics and generate relevant diagrams.

    This is a keyword-based rule engine.
    It does not use an AI model or independently
    verify the technical correctness of the source.
    """

    text = re.sub(r"\s+", " ", str(document_text).lower())

    diagrams = []
    generated_titles = set()

    def add_diagram(diagram):
        """Avoid adding duplicate diagrams."""

        title = diagram["title"].lower()

        if title not in generated_titles:
            generated_titles.add(title)
            diagrams.append(diagram)

    # --------------------------------------------------
    # 1. COMPLEXITY CLASSES: P, NP, NP-HARD, NP-COMPLETE
    # --------------------------------------------------

    has_polynomial = "polynomial time" in text
    has_nondeterministic = "nondeterministic" in text

    if has_polynomial and has_nondeterministic:

        add_diagram(
            create_concept_map(
                "Complexity Classes",
                [
                    ("P", "Problems solvable in polynomial time"),
                    ("NP", "Solutions verifiable in polynomial time"),
                    ("NP-Hard", "At least as hard as every problem in NP"),
                    ("NP-Complete", "Problems belonging to both NP and NP-Hard")
                ]
            )
        )

    # --------------------------------------------------
    # 2. POLYNOMIAL-TIME REDUCTION
    # --------------------------------------------------

    if (
        "reduction" in text
        and ("np-hard" in text or "np-complete" in text)
    ):

        add_diagram(
            create_flowchart(
                "Polynomial-Time Reduction",
                [
                    "Select a known problem A",
                    "Select the target problem B",
                    "Transform an instance of A into an instance of B",
                    "Perform the transformation in polynomial time",
                    "Use the result to establish a relationship between A and B"
                ]
            )
        )

    # --------------------------------------------------
    # 3. SAT / 3-SAT
    # --------------------------------------------------

    if (
        "satisfiability" in text
        or "3-sat" in text
        or re.search(r"\bsat problem\b", text)
    ):

        add_diagram(
            create_decision_flowchart(
                "SAT Problem",
                [
                    "Input a Boolean formula",
                    "Assign True or False values to variables",
                    "Evaluate the Boolean expression"
                ],
                "Is the formula satisfied?",
                "Satisfying assignment found",
                "Try another assignment or report unsatisfiable"
            )
        )

    # --------------------------------------------------
    # 4. APPROXIMATION ALGORITHM
    # --------------------------------------------------

    if "approximation algorithm" in text:

        add_diagram(
            create_flowchart(
                "Approximation Algorithm",
                [
                    "Input an optimization problem",
                    "Identify the objective and constraints",
                    "Apply an approximation strategy",
                    "Generate an approximate solution",
                    "Evaluate the solution quality",
                    "Compare with the approximation guarantee"
                ]
            )
        )

    # --------------------------------------------------
    # 5. GREEDY ALGORITHM
    # --------------------------------------------------

    if (
        "greedy algorithm" in text
        or "greedy method" in text
        or "greedy approach" in text
    ):

        add_diagram(
            create_flowchart(
                "Greedy Algorithm",
                [
                    "Initialize the solution",
                    "Identify available choices",
                    "Select the locally best choice",
                    "Check whether the choice is feasible",
                    "Add the choice to the solution",
                    "Repeat until the solution is complete"
                ]
            )
        )

    # --------------------------------------------------
    # 6. DYNAMIC PROGRAMMING
    # --------------------------------------------------

    if (
        "dynamic programming" in text
        or "dynamic programming approach" in text
    ):

        add_diagram(
            create_flowchart(
                "Dynamic Programming",
                [
                    "Identify overlapping subproblems",
                    "Define the state and recurrence relation",
                    "Establish base cases",
                    "Store previously calculated results",
                    "Reuse stored results",
                    "Construct the final solution"
                ]
            )
        )

    # --------------------------------------------------
    # 7. DIVIDE AND CONQUER
    # --------------------------------------------------

    if (
        "divide and conquer" in text
        or "divide-and-conquer" in text
    ):

        add_diagram(
            create_flowchart(
                "Divide and Conquer",
                [
                    "Start with the original problem",
                    "Divide the problem into smaller subproblems",
                    "Solve each subproblem recursively",
                    "Combine the subproblem solutions",
                    "Return the final solution"
                ]
            )
        )

    # --------------------------------------------------
    # 8. BRANCH AND BOUND
    # --------------------------------------------------

    if "branch and bound" in text:

        add_diagram(
            create_flowchart(
                "Branch and Bound",
                [
                    "Initialize the search space",
                    "Select a candidate node",
                    "Branch into smaller subproblems",
                    "Calculate the bound for each node",
                    "Prune nodes that cannot improve the solution",
                    "Continue searching promising nodes",
                    "Return the best solution"
                ]
            )
        )

    # --------------------------------------------------
    # 9. BACKTRACKING
    # --------------------------------------------------

    if "backtracking" in text:

        add_diagram(
            create_decision_flowchart(
                "Backtracking Algorithm",
                [
                    "Start with an empty solution",
                    "Choose a possible candidate",
                    "Add the candidate to the current solution"
                ],
                "Does the candidate satisfy the constraints?",
                "Continue exploring the next choice",
                "Remove the candidate and try another choice"
            )
        )

    # --------------------------------------------------
    # 10. TIME AND SPACE COMPLEXITY
    # --------------------------------------------------

    if (
        "time complexity" in text
        and "space complexity" in text
    ):

        add_diagram(
            create_concept_map(
                "Algorithm Complexity Analysis",
                [
                    ("Time Complexity", "Measures execution time growth"),
                    ("Space Complexity", "Measures memory usage"),
                    ("Big O", "Upper-bound notation"),
                    ("Big Omega", "Lower-bound notation"),
                    ("Big Theta", "Tight-bound notation")
                ]
            )
        )

    return diagrams
