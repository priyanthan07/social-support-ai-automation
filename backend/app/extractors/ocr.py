"""Image OCR via Tesseract (for Emirates ID and other scanned documents)."""

from __future__ import annotations

from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def ocr_image(path: str | Path) -> str:
    """Return OCR text from an image. Returns '' on failure (logged)."""
    try:
        import pytesseract
        from PIL import Image

        with Image.open(path) as img:
            return pytesseract.image_to_string(img)
    except Exception as exc:  # pragma: no cover - depends on tesseract binary
        logger.warning("OCR failed for %s: %s", path, exc)
        return ""
