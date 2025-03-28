"""
PDF Processor for the Past Paper Concept Analyzer.

This module handles the extraction of text from PDF files.
It supports both native text extraction and OCR for scanned documents.
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict

import pdfplumber
import PyPDF2

# Optional OCR import
try:
    import pytesseract
    from PIL import Image

    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

import config
from models.paper import Paper

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PDFProcessor:
    """
    Handles the extraction of text content from PDF files.

    This class is responsible for:
    1. Reading PDF files from the pdfs/ directory
    2. Extracting text content using multiple methods
    3. Using OCR for scanned papers when necessary
    4. Preprocessing text for analysis
    5. Saving extracted text to the extracted/ directory
    """

    def __init__(self):
        """Initialize the PDFProcessor."""
        self.pdf_dir = config.PDF_DIR
        self.extracted_dir = config.EXTRACTED_DIR

        # Configure OCR if available
        self.ocr_enabled = config.OCR_ENABLED and OCR_AVAILABLE
        if self.ocr_enabled and config.TESSERACT_PATH:
            pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_PATH

        # Create extracted directory if it doesn't exist
        self.extracted_dir.mkdir(exist_ok=True)

    def get_pdf_path(self, paper: Paper) -> Path:
        """
        Get the full path to a paper's PDF file.

        Args:
            paper: Paper object

        Returns:
            Path to the PDF file
        """
        return self.pdf_dir / paper.filename

    def get_output_path(self, paper: Paper) -> Path:
        """
        Get the path where extracted text should be saved.

        Args:
            paper: Paper object

        Returns:
            Path where extracted text will be saved
        """
        # Use the same filename but with .txt extension
        base_name = Path(paper.filename).stem
        return self.extracted_dir / f"{base_name}.json"

    def extract_text_with_pypdf2(self, pdf_path: Path) -> Dict[int, str]:
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
                    text_by_page[page_num + 1] = page.extract_text()

            logger.info(f"Extracted text from {pdf_path} using PyPDF2")
            return text_by_page
        except Exception as e:
            logger.error(f"Error extracting text with PyPDF2: {e}")
            return {}

    def extract_text_with_pdfplumber(self, pdf_path: Path) -> Dict[int, str]:
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
                    text_by_page[page_num + 1] = page.extract_text()

            logger.info(f"Extracted text from {pdf_path} using pdfplumber")
            return text_by_page
        except Exception as e:
            logger.error(f"Error extracting text with pdfplumber: {e}")
            return {}

    def extract_text_with_ocr(self, pdf_path: Path) -> Dict[int, str]:
        """
        Extract text from a PDF using OCR (for scanned documents).

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary mapping page numbers to extracted text
        """
        if not self.ocr_enabled:
            logger.warning(
                "OCR is not available. Install pytesseract and configure TESSERACT_PATH."
            )
            return {}

        text_by_page = {}
        try:
            # Use a temporary directory for image extraction
            temp_dir = Path("temp_ocr")
            temp_dir.mkdir(exist_ok=True)

            try:
                # Convert PDF to images
                # Note: In a real implementation, you might use a library like pdf2image
                # Here we'll just provide a placeholder

                # Simulate image extraction for demonstration
                from pdf2image import convert_from_path

                images = convert_from_path(pdf_path)

                for i, image in enumerate(images):
                    # Save the image
                    image_path = temp_dir / f"page_{i+1}.png"
                    image.save(image_path)

                    # Apply OCR
                    text = pytesseract.image_to_string(image)
                    text_by_page[i + 1] = text

                logger.info(f"Extracted text from {pdf_path} using OCR")
            finally:
                # Clean up temporary directory
                shutil.rmtree(temp_dir, ignore_errors=True)

            return text_by_page
        except Exception as e:
            logger.error(f"Error extracting text with OCR: {e}")
            return {}

    def is_text_extraction_successful(self, text_by_page: Dict[int, str]) -> bool:
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

    def preprocess_text(self, text_by_page: Dict[int, str]) -> Dict[int, str]:
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

            # Replace multiple newlines with a single one
            processed = " ".join(text.split())

            # TODO: Add more preprocessing steps as needed:
            # - Remove headers/footers
            # - Fix common OCR errors
            # - Normalize whitespace
            # - Handle special characters

            preprocessed[page_num] = processed

        return preprocessed

    def extract_text_from_paper(self, paper: Paper) -> Dict[str, Any]:
        """
        Extract text from a paper's PDF file.

        This method attempts multiple extraction methods in order of preference:
        1. pdfplumber (better layout preservation)
        2. PyPDF2 (fallback)
        3. OCR (if enabled and other methods fail)

        Args:
            paper: Paper object to process

        Returns:
            Dictionary with extracted text and metadata
        """
        pdf_path = self.get_pdf_path(paper)

        # Check if the PDF file exists
        if not pdf_path.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            return {"success": False, "error": "PDF file not found"}

        # Try pdfplumber first (better layout preservation)
        text_by_page = self.extract_text_with_pdfplumber(pdf_path)

        # If pdfplumber failed or didn't get enough text, try PyPDF2
        if not self.is_text_extraction_successful(text_by_page):
            logger.info("pdfplumber extraction insufficient, trying PyPDF2")
            text_by_page = self.extract_text_with_pypdf2(pdf_path)

        # If PyPDF2 failed or didn't get enough text, try OCR
        if not self.is_text_extraction_successful(text_by_page) and self.ocr_enabled:
            logger.info("PyPDF2 extraction insufficient, trying OCR")
            text_by_page = self.extract_text_with_ocr(pdf_path)

        # Check if any extraction method succeeded
        if not self.is_text_extraction_successful(text_by_page):
            logger.error(f"All text extraction methods failed for {pdf_path}")
            return {"success": False, "error": "Text extraction failed"}

        # Preprocess the extracted text
        preprocessed_text = self.preprocess_text(text_by_page)

        # Create the result dictionary
        result = {
            "success": True,
            "paper_id": paper.id,
            "year": paper.year,
            "course": paper.course,
            "paper_number": paper.paper_number,
            "filename": paper.filename,
            "extraction_method": "pdfplumber/PyPDF2/OCR",
            "text_by_page": preprocessed_text,
        }

        return result

    def save_extracted_text(
        self, paper: Paper, extraction_result: Dict[str, Any]
    ) -> bool:
        """
        Save extracted text to a JSON file.

        Args:
            paper: Paper object
            extraction_result: Result from extract_text_from_paper

        Returns:
            True if successful, False otherwise
        """
        # Get the output path
        output_path = self.get_output_path(paper)

        try:
            # Write the extraction result to a JSON file
            with open(output_path, "w", encoding="utf-8") as file:
                json.dump(extraction_result, file, ensure_ascii=False, indent=2)

            logger.info(f"Saved extracted text to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving extracted text: {e}")
            return False

    def process_paper(self, paper: Paper) -> bool:
        """
        Process a paper by extracting text and saving it.

        Args:
            paper: Paper object to process

        Returns:
            True if processing was successful, False otherwise
        """
        logger.info(f"Processing paper: {paper}")

        # Extract text from the paper
        extraction_result = self.extract_text_from_paper(paper)

        # If extraction failed, return False
        if not extraction_result["success"]:
            logger.error(f"Failed to extract text from {paper}")
            return False

        # Save the extracted text
        save_success = self.save_extracted_text(paper, extraction_result)

        return save_success


def main():
    """Run the PDF processor as a standalone script."""
    # Get a list of papers to process
    from paper_ingestor import PaperIngestor

    ingestor = PaperIngestor()

    # First, make sure all papers are registered
    ingestor.process_new_papers()

    # Get papers that need processing
    papers = ingestor.get_papers_for_processing()

    if not papers:
        print("No papers to process.")
        return

    # Process each paper
    processor = PDFProcessor()
    for paper in papers:
        print(f"Processing {paper}...")
        success = processor.process_paper(paper)

        if success:
            print("  Success! Marked as processed.")
            ingestor.mark_paper_processed(paper.id)
        else:
            print("  Failed to process.")


if __name__ == "__main__":
    main()
