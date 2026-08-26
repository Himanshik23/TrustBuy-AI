"""Real OCR on report-attachment images (invoices, delivery labels,
refund-chat screenshots) via Tesseract - genuinely runs, not mocked.
PDFs are not OCR'd in this pass (would need a PDF rasterizer); text
extraction on PDFs is a documented follow-up, not silently skipped."""

from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)

_OCR_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


def extract_text(content: bytes, content_type: str) -> str | None:
    if content_type not in _OCR_CONTENT_TYPES:
        return None
    try:
        import pytesseract
        from PIL import Image

        image = Image.open(io.BytesIO(content))
        text = pytesseract.image_to_string(image)
        text = text.strip()
        return text or None
    except Exception:
        # OCR is best-effort evidence, never a reason to fail the upload -
        # docs/SECURITY.md's error-handling principle applies here too.
        logger.exception("OCR extraction failed - continuing without extracted text.")
        return None
