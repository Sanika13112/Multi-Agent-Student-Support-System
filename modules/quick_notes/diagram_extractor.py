
"""
Original PDF Diagram Extractor
--------------------------------
Extracts:
1. Meaningful embedded images from PDF pages.
2. High-resolution page previews for vector-heavy pages.

Filters tiny icons and decorative images.

The original PDF is never modified.
"""

from pathlib import Path
from uuid import uuid4

import pymupdf


# ==================================================
# CONFIGURATION
# ==================================================

VECTOR_DRAWING_THRESHOLD = 15
RENDER_DPI = 160

# Ignore images smaller than these pixel dimensions.
MIN_IMAGE_WIDTH = 100
MIN_IMAGE_HEIGHT = 80

# Ignore images occupying less than this proportion
# of the PDF page's area.
MIN_DISPLAY_AREA_RATIO = 0.01


# ==================================================
# IMAGE FILTER
# ==================================================

def is_meaningful_image(page, xref, image_data):
    """
    Check whether an embedded image is large enough
    to be useful in study notes.

    Uses both original pixel dimensions and the
    image's displayed size inside the PDF.
    """

    width = image_data.get("width", 0)
    height = image_data.get("height", 0)

    # Filter images with very small pixel dimensions.
    if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
        return False

    # Find where the image appears on the PDF page.
    image_rects = page.get_image_rects(xref)

    # If display position cannot be determined,
    # retain the image based on its pixel dimensions.
    if not image_rects:
        return True

    page_area = page.rect.width * page.rect.height

    if page_area <= 0:
        return False

    # Use the largest displayed occurrence.
    largest_display_area = max(
        rect.width * rect.height
        for rect in image_rects
    )

    display_area_ratio = largest_display_area / page_area

    return display_area_ratio >= MIN_DISPLAY_AREA_RATIO


# ==================================================
# MAIN EXTRACTOR
# ==================================================

def extract_original_diagrams(
    pdf_path,
    output_root="static/generated/quick_notes"
):
    """
    Extract meaningful original PDF images and preserve
    vector-heavy pages as high-resolution previews.

    Parameters:
        pdf_path: Path of the uploaded PDF.
        output_root: Root directory for generated files.

    Returns:
        Dictionary containing extracted image
        and page-preview details.
    """

    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF file not found: {pdf_path}"
        )

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(
            "Only PDF files are supported."
        )

    # Unique folder for each processing request.
    job_id = uuid4().hex

    output_dir = Path(output_root) / job_id

    image_dir = output_dir / "original_images"
    preview_dir = output_dir / "vector_page_previews"

    image_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)

    extracted_images = []
    vector_previews = []

    document = pymupdf.open(str(pdf_path))

    try:

        for page_index, page in enumerate(document):

            page_number = page_index + 1

            # ======================================
            # 1. EXTRACT MEANINGFUL EMBEDDED IMAGES
            # ======================================

            image_list = page.get_images(full=True)

            # Avoid extracting the same image repeatedly
            # from the same page.
            seen_xrefs = set()

            for image_index, image_info in enumerate(image_list):

                xref = image_info[0]

                if xref in seen_xrefs:
                    continue

                seen_xrefs.add(xref)

                image_data = document.extract_image(xref)

                if not image_data:
                    continue

                # Filter tiny icons and decorative images.
                if not is_meaningful_image(
                    page,
                    xref,
                    image_data
                ):
                    continue

                image_bytes = image_data["image"]
                extension = image_data["ext"]

                image_name = (
                    f"page_{page_number}_image_{image_index + 1}"
                    f".{extension}"
                )

                image_path = image_dir / image_name

                image_path.write_bytes(image_bytes)

                extracted_images.append({
                    "type": "original_image",
                    "page": page_number,
                    "filename": image_name,
                    "url": f"/{image_path.as_posix()}",
                    "width": image_data.get("width"),
                    "height": image_data.get("height")
                })

            # ======================================
            # 2. PRESERVE VECTOR-HEAVY PAGES
            # ======================================

            drawings = page.get_drawings()

            drawing_count = len(drawings)

            if drawing_count >= VECTOR_DRAWING_THRESHOLD:

                pixmap = page.get_pixmap(
                    dpi=RENDER_DPI,
                    colorspace=pymupdf.csRGB,
                    alpha=False
                )

                preview_name = (
                    f"page_{page_number}_vector_preview.png"
                )

                preview_path = preview_dir / preview_name

                pixmap.save(str(preview_path))

                vector_previews.append({
                    "type": "vector_page_preview",
                    "page": page_number,
                    "filename": preview_name,
                    "url": f"/{preview_path.as_posix()}",
                    "drawing_count": drawing_count,
                    "width": pixmap.width,
                    "height": pixmap.height
                })

    finally:

        document.close()

    # ==============================================
    # 3. RETURN EXTRACTION RESULTS
    # ==============================================

    return {
        "job_id": job_id,

        "total_images": len(extracted_images),

        "total_vector_previews": len(vector_previews),

        "original_images": extracted_images,

        "vector_previews": vector_previews,

        "output_directory": str(output_dir)
    }
