"""Text extraction from binary files (images, PDFs, DOCX) using OCR + native parsers.

Supported formats:
  - Images: jpg, jpeg, png, heic (via pytesseract + Pillow, Portuguese OCR)
  - PDF: embedded text (via PyMuPDF) or OCR fallback for scanned docs
  - DOCX: native text extraction (via python-docx)
"""
import logging
import subprocess
import tempfile
from pathlib import Path

# Allow large images (e.g. high-res scans) — Pillow default is 89MP
import PIL.Image as _PILImage
_PILImage.MAX_IMAGE_PIXELS = None
from PIL import Image

logger = logging.getLogger("engine.sync.text_extractor")

_OCR_LANG = "por"  # Portuguese — primary language for user's documents


def extract_text(file_path: Path) -> str:
    """Extract text from a binary file based on its extension."""
    suffix = file_path.suffix.lower()
    try:
        if suffix in (".jpg", ".jpeg", ".png"):
            return _ocr_image(file_path)
        elif suffix == ".heic":
            return _extract_heic(file_path)
        elif suffix == ".pdf":
            return _extract_pdf(file_path)
        elif suffix == ".docx":
            return _extract_docx(file_path)
        else:
            logger.debug("No extractor for %s, skipping", suffix)
            return ""
    except Exception as e:
        logger.warning("Failed to extract text from %s: %s", file_path.name, e)
        return ""


# ── Image OCR ────────────────────────────────────────────────────────────

_MAX_PIXELS = 4_000_000  # 4MP target for OCR (speed vs accuracy balance)


def _ocr_image(path: Path) -> str:
    """OCR a single image file with Portuguese language model."""
    import pytesseract
    from PIL import Image, ImageEnhance

    img = Image.open(path)
    img = _maybe_downscale(img)
    # Grayscale conversion dramatically improves OCR accuracy on scanned docs
    img = img.convert("L")
    text = pytesseract.image_to_string(img, lang=_OCR_LANG)
    return text.strip()


def _maybe_downscale(img: Image.Image) -> Image.Image:
    """Downscale image if it exceeds _MAX_PIXELS to speed up OCR."""
    w, h = img.size
    if w * h <= _MAX_PIXELS:
        return img
    ratio = (_MAX_PIXELS / (w * h)) ** 0.5
    new_size = (int(w * ratio), int(h * ratio))
    return img.resize(new_size, Image.LANCZOS)


def _extract_heic(path: Path) -> str:
    """Convert HEIC to PNG via sips (macOS built-in), then OCR."""
    import pytesseract
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        png_path = Path(tmp) / f"{path.stem}.png"
        subprocess.run(
            ["sips", "-s", "format", "png", str(path), "--out", str(png_path)],
            capture_output=True, check=True, timeout=30,
        )
        img = Image.open(png_path)
        text = pytesseract.image_to_string(img, lang=_OCR_LANG)
        return text.strip()


# ── PDF extraction ───────────────────────────────────────────────────────

def _extract_pdf(path: Path) -> str:
    """Extract text from PDF.

    First attempts embedded text extraction (PyMuPDF).
    If less than 50 chars, falls back to page-by-page OCR.
    """
    import fitz  # PyMuPDF
    doc = fitz.open(path)
    parts: list[str] = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text().strip()

        if len(text) < 50:
            # Probably a scanned page — OCR it
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            import pytesseract
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(img_bytes))
            text = pytesseract.image_to_string(img, lang=_OCR_LANG).strip()

        if text:
            parts.append(text)

    doc.close()
    return "\n\n".join(parts)


# ── DOCX extraction ──────────────────────────────────────────────────────

def _extract_docx(path: Path) -> str:
    """Extract text from a .docx file."""
    import docx as _docx
    doc = _docx.Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)
