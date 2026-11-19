
"""
StudyMate AI - Improved QuickNotes Formatter

Formats extracted source content into structured B.Tech study notes.

Supports:
- Topic-wise notes
- Important concepts
- Definitions
- Formulas
- Algorithms
- Examples
- Original PDF vector diagrams
- Generated Mermaid diagrams

No AI model required.
"""


# ==================================================
# 1. GENERAL LIST FORMATTERS
# ==================================================

def format_list(items, empty_message="No content identified."):
    """Format items as Markdown bullet points."""

    if not items:
        return f"- {empty_message}"

    formatted = []
    seen = set()

    for item in items:

        if not isinstance(item, str):
            continue

        item = item.strip()

        if not item:
            continue

        normalized = " ".join(item.lower().split())

        if normalized in seen:
            continue

        seen.add(normalized)

        # Preserve existing bullet formatting
        if item.startswith(("- ", "* ", "• ")):
            formatted.append(item)
        else:
            formatted.append(f"- {item}")

    return "\n".join(formatted) if formatted else f"- {empty_message}"


def format_numbered_list(items, empty_message="No content identified."):
    """Format items as numbered Markdown points."""

    if not items:
        return f"- {empty_message}"

    formatted = []
    seen = set()

    for item in items:

        if not isinstance(item, str):
            continue

        item = item.strip()

        if not item:
            continue

        normalized = " ".join(item.lower().split())

        if normalized in seen:
            continue

        seen.add(normalized)

        # Preserve existing numbered formatting
        if item[:1].isdigit() and (
            "." in item[:5] or ")" in item[:5]
        ):
            formatted.append(item)
        else:
            formatted.append(item)

    if not formatted:
        return f"- {empty_message}"

    return "\n".join(
        f"{index}. {item}"
        for index, item in enumerate(formatted, start=1)
    )


# ==================================================
# 2. TOPIC CONTENT FORMATTER
# ==================================================

def format_topic_content(content):
    """
    Format topic-wise source content.

    Preserves original technical meaning and wording.
    """

    if not content:
        return "- No content identified."

    if isinstance(content, str):
        paragraphs = content.splitlines()

    elif isinstance(content, list):
        paragraphs = content

    else:
        return str(content)

    formatted = []

    for paragraph in paragraphs:

        if not isinstance(paragraph, str):
            continue

        paragraph = paragraph.strip()

        if not paragraph:
            continue

        # Preserve headings
        if paragraph.startswith("#"):
            formatted.append(paragraph)
            continue

        # Preserve bullets
        if paragraph.startswith(("- ", "* ", "• ")):
            formatted.append(paragraph)
            continue

        # Preserve numbered lists
        if (
            paragraph[:1].isdigit()
            and (
                "." in paragraph[:5]
                or ")" in paragraph[:5]
            )
        ):
            formatted.append(paragraph)
            continue

        # Preserve labelled steps
        if paragraph.lower().startswith("step "):
            formatted.append(paragraph)
            continue

        formatted.append(f"- {paragraph}")

    return "\n\n".join(formatted) if formatted else "- No content identified."


# ==================================================
# 3. DIAGRAM FORMATTER
# ==================================================

def format_diagrams(
    original_diagrams=None,
    generated_diagrams=None
):
    """
    Format original PDF diagrams and generated Mermaid diagrams.
    """

    original_diagrams = original_diagrams or []
    generated_diagrams = generated_diagrams or []

    sections = []

    # --------------------------------------------------
    # ORIGINAL PDF DIAGRAMS
    # --------------------------------------------------

    sections.append("### Original PDF Diagrams\n")

    valid_original = [
        diagram
        for diagram in original_diagrams
        if isinstance(diagram, dict)
        and diagram.get("url")
    ]

    if valid_original:

        for index, diagram in enumerate(valid_original, start=1):

            page = diagram.get("page", "Unknown")
            title = diagram.get(
                "filename",
                f"Original Diagram {index}"
            )

            url = diagram.get("url")

            sections.append(
                f"#### Diagram {index} - Page {page}\n\n"
                f"![{title}]({url})\n"
            )

    else:
        sections.append(
            "- No original PDF diagrams available.\n"
        )

    # --------------------------------------------------
    # GENERATED MERMAID DIAGRAMS
    # --------------------------------------------------

    sections.append("### Generated Diagrams\n")

    valid_generated = []

    for index, diagram in enumerate(generated_diagrams, start=1):

        if isinstance(diagram, str):

            title = f"Generated Diagram {index}"
            mermaid = diagram

        elif isinstance(diagram, dict):

            title = (
                diagram.get("title")
                or diagram.get("name")
                or f"Generated Diagram {index}"
            )

            mermaid = (
                diagram.get("mermaid")
                or diagram.get("code")
                or diagram.get("content")
                or diagram.get("diagram")
                or ""
            )

        else:
            continue

        if isinstance(mermaid, str) and mermaid.strip():

            valid_generated.append(
                (title, mermaid.strip())
            )

    if valid_generated:

        for title, mermaid in valid_generated:

            sections.append(
                f"#### {title}\n\n"
                f"```mermaid\n"
                f"{mermaid}\n"
                f"```\n"
            )

    else:
        sections.append(
            "- No generated diagrams available.\n"
        )

    return "\n".join(sections)


# ==================================================
# 4. SECTION FORMATTER
# ==================================================

def format_section(title, content, empty_message):
    """Format a standard study-notes section."""

    return (
        f"## {title}\n\n"
        f"{format_list(content, empty_message)}\n"
    )


# ==================================================
# 5. COMPLETE STUDY NOTES FORMATTER
# ==================================================

def format_study_notes(
    document_name,
    classified_content,
    original_diagrams=None,
    generated_diagrams=None,
    topic_sections=None
):
    """
    Generate complete structured B.Tech study notes.

    Parameters:
        document_name:
            Original document filename.

        classified_content:
            Output from classify_document().

        original_diagrams:
            Original PDF vector previews.

        generated_diagrams:
            Generated Mermaid diagrams.

        topic_sections:
            Topic-wise source content.

    Returns:
        Markdown study notes.
    """

    classified_content = classified_content or {}
    topic_sections = topic_sections or {}

    definitions = classified_content.get("definitions", [])
    examples = classified_content.get("examples", [])
    formulas = classified_content.get("formulas", [])
    algorithms = classified_content.get("algorithms", [])
    important_points = classified_content.get("important_points", [])

    # Ensure content values are lists
    definitions = definitions if isinstance(definitions, list) else []
    examples = examples if isinstance(examples, list) else []
    formulas = formulas if isinstance(formulas, list) else []
    algorithms = algorithms if isinstance(algorithms, list) else []
    important_points = (
        important_points
        if isinstance(important_points, list)
        else []
    )

    notes = []

    # --------------------------------------------------
    # TITLE
    # --------------------------------------------------

    notes.append(f"# Study Notes: {document_name}\n")

    notes.append(
        "> Generated by StudyMate AI - QuickNotes\n"
    )

    notes.append(
        "---\n"
    )

    # --------------------------------------------------
    # 1. DOCUMENT OVERVIEW
    # --------------------------------------------------

    notes.append("## 1. Document Overview\n")

    notes.append(f"- **Document:** {document_name}")
    notes.append("- **Processing:** Fast Python-based extraction")
    notes.append("- **Purpose:** Organized B.Tech study and revision material")
    notes.append("- **Content:** Topic-wise notes, definitions, formulas, examples and diagrams")

    notes.append("")

    # --------------------------------------------------
    # 2. TOPIC-WISE NOTES
    # --------------------------------------------------

    notes.append("## 2. Topic-wise Notes\n")

    if topic_sections:

        for index, (topic, content) in enumerate(
            topic_sections.items(),
            start=1
        ):

            notes.append(
                f"### 2.{index} {topic}\n"
            )

            notes.append(
                format_topic_content(content)
            )

            notes.append("")

    else:

        notes.append(
            "- No topic headings were identified in the document.\n"
        )

    # --------------------------------------------------
    # 3. IMPORTANT CONCEPTS
    # --------------------------------------------------

    notes.append(
        format_section(
            "3. Important Concepts",
            important_points,
            "No important concepts identified."
        )
    )

    # --------------------------------------------------
    # 4. DEFINITIONS
    # --------------------------------------------------

    notes.append("## 4. Important Definitions\n")

    notes.append(
        format_numbered_list(
            definitions,
            "No definitions identified."
        )
    )

    notes.append("")

    # --------------------------------------------------
    # 5. FORMULAS
    # --------------------------------------------------

    notes.append("## 5. Important Formulas and Equations\n")

    notes.append(
        format_list(
            formulas,
            "No formulas identified."
        )
    )

    notes.append("")

    # --------------------------------------------------
    # 6. ALGORITHMS
    # --------------------------------------------------

    notes.append("## 6. Algorithms and Steps\n")

    notes.append(
        format_numbered_list(
            algorithms,
            "No algorithms identified."
        )
    )

    notes.append("")

    # --------------------------------------------------
    # 7. EXAMPLES
    # --------------------------------------------------

    notes.append("## 7. Important Examples\n")

    notes.append(
        format_numbered_list(
            examples,
            "No examples identified."
        )
    )

    notes.append("")

    # --------------------------------------------------
    # 8. DIAGRAMS
    # --------------------------------------------------

    notes.append("## 8. Diagrams\n")

    notes.append(
        format_diagrams(
            original_diagrams=original_diagrams,
            generated_diagrams=generated_diagrams
        )
    )

    notes.append("")

    # --------------------------------------------------
    # 9. QUICK REVISION
    # --------------------------------------------------

    notes.append("## 9. Quick Revision\n")

    revision_points = important_points[:10]

    notes.append(
        format_list(
            revision_points,
            "Revision points will be added when content is identified."
        )
    )

    notes.append("")

    # --------------------------------------------------
    # 10. EXAM PREPARATION
    # --------------------------------------------------

    notes.append("## 10. Exam Preparation\n")

    notes.append(
        "- Revise all important definitions and technical concepts.\n"
        "- Understand the working of each algorithm step by step.\n"
        "- Practice the formulas and numerical examples.\n"
        "- Study the original PDF diagrams and generated flowcharts.\n"
        "- Prepare short answers for important concepts.\n"
        "- Refer to the source document to verify extracted content.\n"
    )

    notes.append("\n---\n")
    notes.append(
        "*End of Study Notes - StudyMate AI*\n"
    )

    return "\n".join(notes)
