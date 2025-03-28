"""
PDF processing utilities for the Past Paper Concept Analyzer.

This module provides functions for extracting text from PDFs using various methods
and preprocessing the extracted text.
"""

import logging
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple

import pdfplumber
import PyPDF2

from utils.logging_config import setup_logger

# Configure logger
logger = setup_logger(__name__, logging.INFO)

# Try to import OCR-related packages
try:
    import pytesseract
    from PIL import Image
    from pdf2image import convert_from_path

    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning(
        "OCR dependencies not available. Install pytesseract, pdf2image, and Pillow "
        "for OCR support."
    )


def extract_text_with_pypdf2(pdf_path: Path) -> Dict[int, str]:
    """
    Extract text from a PDF using PyPDF2.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Dictionary mapping page numbers to extracted text
    """
    text_by_page = {}

    try:
        with open(pdf_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                text_by_page[page_num + 1] = page.extract_text() or ""

        logger.info(f"Extracted text from {pdf_path} using PyPDF2")
        return text_by_page
    except Exception as e:
        logger.error(f"Error extracting text with PyPDF2: {e}")
        return {}


def extract_text_with_pdfplumber(pdf_path: Path) -> Dict[int, str]:
    """
    Extract text from a PDF using pdfplumber (better layout preservation).

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Dictionary mapping page numbers to extracted text
    """
    text_by_page = {}

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                extracted_text = page.extract_text()
                text_by_page[page_num + 1] = extracted_text or ""

        logger.info(f"Extracted text from {pdf_path} using pdfplumber")
        return text_by_page
    except Exception as e:
        logger.error(f"Error extracting text with pdfplumber: {e}")
        return {}


def extract_text_with_ocr(
    pdf_path: Path, 
    tesseract_path: Optional[str] = None,
    dpi: int = 300
) -> Dict[int, str]:
    """
    Extract text from a PDF using OCR (for scanned documents).

    Args:
        pdf_path: Path to the PDF file
        tesseract_path: Optional path to Tesseract executable
        dpi: Resolution for PDF to image conversion (higher is better but slower)

    Returns:
        Dictionary mapping page numbers to extracted text
    """
    if not OCR_AVAILABLE:
        logger.warning(
            "OCR is not available. Install pytesseract, pdf2image, and Pillow."
        )
        return {}

    # Configure Tesseract path if provided
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

    text_by_page = {}
    
    # Create a temporary directory for image extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Convert PDF to images
            images = convert_from_path(pdf_path, dpi=dpi)

            # Process each image
            for i, image in enumerate(images):
                # Apply OCR to extract text
                text = pytesseract.image_to_string(image)
                text_by_page[i + 1] = text or ""

            logger.info(f"Extracted text from {pdf_path} using OCR")
            return text_by_page
            
        except Exception as e:
            logger.error(f"Error extracting text with OCR: {e}")
            return {}


def preprocess_text(text_by_page: Dict[int, str]) -> Dict[int, str]:
    """
    Preprocess extracted text for better analysis.

    Args:
        text_by_page: Dictionary mapping page numbers to extracted text

    Returns:
        Dictionary mapping page numbers to preprocessed text
    """
    preprocessed = {}

    for page_num, text in text_by_page.items():
        if not text:
            preprocessed[page_num] = ""
            continue

        # Clean whitespace and normalize
        lines = text.split('\n')
        cleaned_lines = [line.strip() for line in lines]
        
        # Remove empty lines
        non_empty_lines = [line for line in cleaned_lines if line]
        
        # Join with proper spacing
        processed = ' '.join(non_empty_lines)
        
        # Replace multiple spaces with single space
        processed = ' '.join(processed.split())

        preprocessed[page_num] = processed

    return preprocessed


def is_text_extraction_successful(text_by_page: Dict[int, str]) -> bool:
    """
    Check if text extraction was successful.

    Args:
        text_by_page: Dictionary mapping page numbers to extracted text

    Returns:
        True if extraction was successful, False otherwise
    """
    # If we have no pages, extraction failed
    if not text_by_page:
        return False

    # Count pages with significant text
    pages_with_text = sum(
        1 for text in text_by_page.values() if text and len(text.strip()) > 100
    )

    # If less than half the pages have text, consider it unsuccessful
    return pages_with_text >= len(text_by_page) / 2


def extract_text_from_pdf(
    pdf_path: Path, 
    ocr_enabled: bool = False,
    tesseract_path: Optional[str] = None
) -> Tuple[Dict[int, str], str]:
    """
    Extract text from a PDF file using multiple methods.

    This function tries multiple extraction methods in order:
    1. pdfplumber (better layout preservation)
    2. PyPDF2 (fallback)
    3. OCR (if enabled and other methods fail)

    Args:
        pdf_path: Path to the PDF file
        ocr_enabled: Whether to try OCR if other methods fail
        tesseract_path: Path to Tesseract executable (for OCR)

    Returns:
        Tuple of (extracted text by page, method used)
    """
    # Check if the PDF file exists
    if not pdf_path.exists():
        logger.error(f"PDF file not found: {pdf_path}")
        return {}, "failed"

    # Try pdfplumber first (better layout preservation)
    text_by_page = extract_text_with_pdfplumber(pdf_path)
    method = "pdfplumber"

    # If pdfplumber failed or didn't get enough text, try PyPDF2
    if not is_text_extraction_successful(text_by_page):
        logger.info("pdfplumber extraction insufficient, trying PyPDF2")
        text_by_page = extract_text_with_pypdf2(pdf_path)
        method = "PyPDF2"

    # If PyPDF2 failed or didn't get enough text, try OCR
    if not is_text_extraction_successful(text_by_page) and ocr_enabled:
        logger.info("PyPDF2 extraction insufficient, trying OCR")
        text_by_page = extract_text_with_ocr(pdf_path, tesseract_path)
        method = "OCR"

    # Check if any extraction method succeeded
    if not is_text_extraction_successful(text_by_page):
        logger.error(f"All text extraction methods failed for {pdf_path}")
        return {}, "failed"

    # Preprocess the extracted text
    preprocessed_text = preprocess_text(text_by_page)
    return preprocessed_text, method
