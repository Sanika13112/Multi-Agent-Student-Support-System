"""
run_pipeline.py - run the full NLP pipeline (CO1-CO4) from the command line.

Examples (Windows):
    python run_pipeline.py data\\DAA_Unit5_Computational_Complexity.pdf
    python run_pipeline.py notes.pdf --translate mr
    python run_pipeline.py notes.txt --no-llm --topics 4

Writes two files into reports/:
    <name>_pipeline.json   every stage's full output (for checking numbers)
    <name>_pipeline.md     a readable report to show or submit

Stage 10 (LLM) needs Ollama running with the project's Qwen model.
Stage 11 (translation) needs internet; it runs only with --translate.
"""

import argparse
import json
import sys
from pathlib import Path

from nlp.pipeline import run_pipeline, render_markdown

STATUS_MARK = {"done": "OK  ", "skipped": "SKIP", "failed": "FAIL"}


def parse_args():
    """Read the command-line options."""

    parser = argparse.ArgumentParser(description="Run the StudyMate AI NLP pipeline on one document.")
    parser.add_argument("document", help="PDF or TXT file to analyse")
    parser.add_argument("--no-llm", action="store_true", help="skip stage 10 (Ollama LLM summary)")
    parser.add_argument("--translate", choices=["hi", "mr"], help="translate the summary to Hindi (hi) or Marathi (mr)")
    parser.add_argument("--topics", type=int, default=5, help="number of LDA topics (2-15, default 5)")
    parser.add_argument("--out-dir", default="reports", help="folder for the reports (default: reports)")
    return parser.parse_args()


def main():
    """Run the pipeline, print one line per stage, save the JSON and Markdown reports."""

    args = parse_args()
    document = Path(args.document)

    if not document.is_file():
        print(f"File not found: {document}")
        return 1

    print(f"\nRunning the NLP pipeline on {document.name} ...\n")
    report = run_pipeline(
        file_path=str(document),
        use_llm=not args.no_llm,
        translate_to=args.translate,
        num_topics=max(2, min(args.topics, 15)),
    )

    for stage in report["stages"]:
        print(f"[{STATUS_MARK[stage['status']]}] {stage['co']}  {stage['number']:>2}. "
              f"{stage['title']:<40} {stage['seconds']:>6.2f}s  {stage['summary']}")

    totals = report["totals"]
    print(f"\n{totals['done']}/{totals['stages']} stages done, {totals['skipped']} skipped, "
          f"{totals['failed']} failed in {totals['seconds']} s")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{document.stem}_pipeline.json"
    markdown_path = out_dir / f"{document.stem}_pipeline.md"

    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")

    print(f"Reports saved: {json_path}  and  {markdown_path}\n")
    return 1 if totals["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
