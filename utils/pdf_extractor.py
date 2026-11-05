"""
PDF text extraction utilities.

Supports PyMuPDF (fitz) for native text extraction and Tesseract OCR
as a fallback for scanned/image-based PDFs.
"""

import os
import tempfile
from typing import Optional

try:
    import pymupdf  # PyMuPDF (modern import path)
except ImportError:  # pragma: no cover
    try:
        import fitz as pymupdf  # Legacy fallback
    except ImportError:
        pymupdf = None

try:
    import pytesseract
    from PIL import Image
except ImportError:  # pragma: no cover
    pytesseract = None
    Image = None


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file using PyMuPDF. Falls back to Tesseract OCR
    for scanned/image pages when PyMuPDF yields no readable text.

    Args:
        file_path: Path to the PDF file.

    Returns:
        Extracted text as a single string.
    """
    text_parts = []

    # Primary: PyMuPDF native text extraction
    if pymupdf is not None:
        try:
            doc = pymupdf.open(file_path)
            for page in doc:
                page_text = page.get_text()
                if page_text.strip():
                    text_parts.append(page_text)
            doc.close()
        except Exception:
            pass

    # Fallback: Tesseract OCR for scanned/image PDFs
    if not text_parts and pytesseract is not None and Image is not None and pymupdf is not None:
        try:
            doc = pymupdf.open(file_path)
            for page in doc:
                pix = page.get_pixmap(matrix=pymupdf.Matrix(2.0, 2.0))
                img_path = os.path.join(tempfile.gettempdir(), f"page_{page.number}.png")
                pix.save(img_path)
                ocr_text = pytesseract.image_to_string(Image.open(img_path))
                text_parts.append(ocr_text)
                try:
                    os.remove(img_path)
                except OSError:
                    pass
            doc.close()
        except Exception:
            pass

    return "\n".join(text_parts).strip()
