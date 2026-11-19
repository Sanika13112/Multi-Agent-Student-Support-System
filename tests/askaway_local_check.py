"""
AskAway local verification (real all-MiniLM-L6-v2 + real Qwen via Ollama).

Run from the project root (Multi-Agent-Student-Support-System) with your venv active:

    python tests\\askaway_local_check.py                    # retrieval + errors (no Ollama needed)
    python tests\\askaway_local_check.py --with-llm         # also asks Qwen (Ollama must be running)
    python tests\\askaway_local_check.py --pdf "C:\\path\\DAA_Unit5.pdf" --with-llm
        (optionally add --question "What is Cook's theorem?" to test your own PDF)

It prints PASS/FAIL per check plus cosine scores, so the thresholds in
modules/ask_away/service.py can be tuned against the real embedding model.
"""

import argparse
import os
import sys
import tempfile
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from modules.ask_away import service as S  # noqa: E402

SAMPLE_TEXT = """Computational Complexity Basics

A decision problem is a problem whose answer is either yes or no. The class P contains all decision problems that can be solved by a deterministic algorithm in polynomial time, that is in O(n^k) time for some constant k. Problems in P are considered tractable. The class NP contains decision problems whose solutions can be verified in polynomial time by a deterministic algorithm. Every problem in P is also in NP, so P is a subset of NP. Whether P equals NP is an open question.

Reductions and NP-Completeness

A polynomial time reduction from problem A to problem B transforms every instance of A into an instance of B in polynomial time such that the answers are the same. We write A <=p B. A problem B is NP-hard if every problem in NP reduces to B in polynomial time. A problem is NP-complete if it is in NP and it is NP-hard. If any NP-complete problem can be solved in polynomial time then P = NP.

Cook's Theorem and SAT

The Boolean satisfiability problem SAT asks whether there is an assignment of truth values to variables that makes a Boolean formula true. Cook's theorem states that SAT is NP-complete. It was the first problem proved to be NP-complete. The 3-SAT problem restricts each clause to exactly three literals and is also NP-complete. Other NP-complete problems include vertex cover, clique, Hamiltonian cycle and the travelling salesman decision problem.

Approximation Algorithms

An approximation algorithm has approximation ratio rho(n) if the cost C of its solution is within a factor rho(n) of the cost C* of an optimal solution: max(C/C*, C*/C) <= rho(n). APPROX-VERTEX-COVER repeatedly picks an edge (u, v), adds both u and v to the cover and removes all edges incident on u or v. It is a 2-approximation algorithm.
"""

IN_DOCUMENT = [
    ("What is Cook's theorem?", "Cook"),
    ("Define NP-hard", "NP-hard"),
    ("SAT", "satisfiability"),
    ("What is class P?", "class P"),
    ("What is the approximation ratio of APPROX-VERTEX-COVER?", "APPROX-VERTEX-COVER"),
    ("Explain polynomial time reduction", "reduction"),
]
OUT_OF_DOCUMENT = [
    "Explain photosynthesis",
    "What is the capital of France?",
    "Explain Newton's laws of motion",
]

results = []


def check(name, condition, detail=""):
    results.append(bool(condition))
    status = "PASS" if condition else "FAIL"
    print(f"{status}  {name}" + (f"   [{detail}]" if detail else ""))


def expect_error(name, func, text):
    try:
        func()
        check(name, False, "no error raised")
    except Exception as exc:  # noqa: BLE001
        check(name, text.lower() in str(exc).lower(), f"{type(exc).__name__}: {str(exc)[:90]}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-llm", action="store_true", help="Also call Qwen through Ollama")
    parser.add_argument("--pdf", help="Optional path to one of your own PDFs")
    parser.add_argument("--question", help="Question to ask about --pdf")
    args = parser.parse_args()

    workdir = tempfile.mkdtemp(prefix="askaway_check_")
    sample_path = os.path.join(workdir, "DAA_Unit5_sample.txt")
    with open(sample_path, "w", encoding="utf-8") as handle:
        handle.write(SAMPLE_TEXT)

    print("\n== 1. Embedding model ==")
    started = time.perf_counter()
    S.warm_up()
    check("all-MiniLM-L6-v2 loads on CPU", True, f"{time.perf_counter() - started:.1f}s")
    first = S.get_embedding_model()
    check("model is cached (not reloaded)", S.get_embedding_model() is first)

    print("\n== 2. TXT upload ==")
    info = S.upload_document(sample_path, "check-user-a")
    check("TXT upload", info["success"], f"{info['chunk_count']} chunks")

    print("\n== 3. Retrieval with the real model (scores help tune thresholds) ==")
    for question, must_contain in IN_DOCUMENT:
        hits = S.retrieve_relevant_chunks(question, "check-user-a")
        scores = ", ".join(f"cos={h['score']:.2f}/kw={h['keyword_score']:.2f}" for h in hits)
        check(
            f"in-document: {question}",
            hits and must_contain.lower() in hits[0]["text"].lower(),
            scores or "nothing retrieved",
        )

    for question in OUT_OF_DOCUMENT:
        hits = S.retrieve_relevant_chunks(question, "check-user-a")
        check(
            f"off-topic rejected: {question}",
            not hits,
            ", ".join(f"cos={h['score']:.2f}" for h in hits) or "no chunks",
        )

    print("\n== 4. Error handling ==")
    bad_type = os.path.join(workdir, "notes.docx")
    empty = os.path.join(workdir, "empty.txt")
    open(bad_type, "wb").write(b"fake")
    open(empty, "w").close()
    expect_error("invalid file type", lambda: S.upload_document(bad_type, "e"), "pdf or txt")
    expect_error("empty file", lambda: S.upload_document(empty, "e"), "empty")
    expect_error("missing file", lambda: S.upload_document(os.path.join(workdir, "nope.pdf"), "e"), "not be found")
    expect_error("empty question", lambda: S.ask_question("  ", "check-user-a"), "enter a question")
    expect_error("no document in session", lambda: S.ask_question("What is P?", "check-nobody"), "upload a document")

    print("\n== 5. Session isolation ==")
    check("user B has no document", S.get_document_info("check-user-b")["success"] is False)
    S.clear_document("check-user-b")
    check("clearing B keeps A", S.get_document_info("check-user-a")["success"] is True)

    if args.pdf:
        print("\n== 6. Your PDF ==")
        info = S.upload_document(args.pdf, "check-user-pdf")
        print(f"      pages={info['page_count']} chunks={info['chunk_count']} warnings={info.get('warnings')}")
        check("PDF upload", info["success"])
        if args.question:
            hits = S.retrieve_relevant_chunks(args.question, "check-user-pdf")
            for h in hits:
                print(f"      page {h['page_number']} chunk {h['chunk_index'] + 1} cos={h['score']:.2f}: {h['text'][:90]!r}")
            check("PDF retrieval returns page numbers", hits and all(h["page_number"] for h in hits),
                  "open the PDF and confirm these pages contain the answer")

    if args.with_llm:
        print("\n== 7. Qwen answers (Ollama must be running) ==")
        for question in ["What is Cook's theorem?", "Explain NP-completeness in detail"]:
            started = time.perf_counter()
            reply = S.ask_question(question, "check-user-a")
            seconds = time.perf_counter() - started
            print(f"\n--- {question}  ({seconds:.1f}s)\n{reply['answer']}\n")
            check(f"grounded answer with sources: {question}", reply["sources"] and reply["answer"] != S.NOT_AVAILABLE_MESSAGE)

        reply = S.ask_question("Explain photosynthesis", "check-user-a")
        check("off-topic -> exact refusal, no sources",
              reply["answer"] == S.NOT_AVAILABLE_MESSAGE and not reply["sources"])

        if args.pdf and args.question:
            reply = S.ask_question(args.question, "check-user-pdf")
            print(f"\n--- {args.question}\n{reply['answer']}")
            print("      sources:", [(s["page_number"], s["chunk_index"], s["relevance_score"]) for s in reply["sources"]])

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
