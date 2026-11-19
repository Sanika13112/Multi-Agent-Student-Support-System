
from modules.quick_notes.diagram_generator import generate_diagrams


sample_text = """
Computational complexity studies algorithm efficiency.
P represents polynomial time.
NP represents nondeterministic polynomial time.
Polynomial time reduction is used for NP-Hard problems.
SAT is a Boolean satisfiability problem.
Approximation algorithm is used for optimization problems.
"""


diagrams = generate_diagrams(sample_text)

print("\n========== GENERATED DIAGRAMS ==========")

for diagram in diagrams:

    print("\nTitle:", diagram["title"])
    print("Type:", diagram["type"])
    print("\nMermaid code:")
    print(diagram["mermaid"])

print("\nTotal diagrams generated:", len(diagrams))
