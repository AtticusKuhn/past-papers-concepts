"""
Paper Ingestor for the Past Paper Concept Analyzer.

This module handles the discovery, validation, and registration of PDF papers.
It monitors the pdfs/ directory and registers new files in the database as they are added.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from sqlalchemy.exc import IntegrityError

import config
from models.base import db_session, init_db
from models.paper import Paper
from utils.logging_config import setup_logger

# Configure logger
logger = setup_logger(__name__, logging.INFO, "logs/paper_ingestor.log")


class PaperIngestor:
    """
    Handles the ingestion of PDF papers into the system.

    This class is responsible for:
    1. Discovering PDF files in the pdfs/ directory
    2. Extracting metadata from filenames or content
    3. Registering papers in the database
    4. Providing access to papers for processing
    """

    # Regex patterns for extracting metadata from filenames
    FILENAME_PATTERNS = [
        # Format: YEAR-pXX-qYY-solutions.pdf (e.g., 2021-p07-q08-solutions.pdf)
        re.compile(r"(\d{4})-p(\d{2})-q(\d{2})-solutions\.pdf", re.IGNORECASE),
        re.compile(r"y(\d{4})p(\d+)q(\d+)\.pdf", re.IGNORECASE),
        
        # Alternative format: YEAR_pXX_qYY.pdf (e.g., 2021_p07_q08.pdf)
        re.compile(r"(\d{4})_p(\d{2})_q(\d{2})(?:_solutions)?\.pdf", re.IGNORECASE),
        
        # Another alternative: YEAR_Paper_XX_Question_YY.pdf
        re.compile(
            r"(\d{4})_Paper_(\d+)_Question_(\d+)(?:_solutions)?\.pdf", 
            re.IGNORECASE
        ),
    ]

    def __init__(self):
        """Initialize the PaperIngestor."""
        # Ensure database tables exist
        init_db()
        self.pdf_dir = config.PDF_DIR

    def find_new_papers(self) -> List[Path]:
        """
        Find PDF files in the pdfs/ directory that haven't been registered.

        Returns:
            List of Path objects for unregistered PDF files
        """
        # Get list of PDF files
        pdf_files = list(self.pdf_dir.glob("*.pdf"))
        
        if not pdf_files:
            logger.info(f"No PDF files found in {self.pdf_dir}")
            return []

        # Get list of already registered filenames from database
        with db_session() as db:
            existing_filenames = {
                paper.filename for paper in db.query(Paper.filename).all()
            }

        # Filter to only new files
        new_files = [pdf for pdf in pdf_files if pdf.name not in existing_filenames]
        
        if new_files:
            logger.info(f"Found {len(new_files)} new papers to process")
            for pdf in new_files:
                logger.debug(f"New paper found: {pdf.name}")
        else:
            logger.info("No new papers found")
            
        return new_files

    def extract_metadata(self, pdf_path: Path) -> Dict[str, Optional[Union[int, str]]]:
        """
        Extract metadata from a PDF filename using multiple patterns.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary with metadata (year, course, paper_number) or empty if extraction fails
        """
        filename = pdf_path.name
        
        # Try each pattern until one matches
        for pattern in self.FILENAME_PATTERNS:
            match = pattern.match(filename)
            if match:
                year = int(match.group(1))
                paper_number = int(match.group(2))
                question_number = int(match.group(3))
                # Using question number as the course for compatibility with existing code
                course = f"q{question_number}"
                
                return {
                    "year": year,
                    "course": course,
                    "paper_number": paper_number,
                    "filename": filename
                }
        
        # If no pattern matches, log a warning and return empty metadata
        logger.warning(f"Could not extract metadata from filename: {filename}")
        return {}

    def register_paper(self, pdf_path: Path) -> Optional[Paper]:
        """
        Register a paper in the database.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Registered Paper object or None if registration fails
        """
        metadata = self.extract_metadata(pdf_path)
        
        if not metadata:
            logger.error(f"Failed to extract metadata for {pdf_path.name}, skipping registration")
            return None
        
        if not all(key in metadata for key in ["year", "course", "paper_number"]):
            logger.error(f"Incomplete metadata for {pdf_path.name}, skipping registration")
            return None

        try:
            with db_session() as db:
                # Check if paper already exists
                existing_paper = db.query(Paper).filter(Paper.filename == pdf_path.name).first()
                if existing_paper:
                    logger.warning(f"Paper already exists in database: {pdf_path.name}")
                    return existing_paper
                   
                
                # Create new Paper object
                new_paper = Paper(
                    year=metadata["year"],
                    course=metadata["course"],
                    paper_number=metadata["paper_number"],
                    filename=pdf_path.name
                )
                
                db.add(new_paper)                               
                
                logger.info(
                    f"Registered paper: {new_paper}"
                    f"(Year: {metadata['year']}, Course: {metadata['course']})"
                )
               
                return new_paper
                
        except IntegrityError as e:
            logger.warning(f"Paper already exists in database (integrity error): {pdf_path.name}")
            logger.debug(f"IntegrityError details: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error registering paper {pdf_path.name}: {str(e)}")
            return None

    def process_new_papers(self) -> List[Paper]:
        """
        Find and register all new papers.

        Returns:
            List of registered Paper objects
        """
        new_pdf_files = self.find_new_papers()
        
        if not new_pdf_files:
            return []
            
        registered_papers = []

        for pdf_path in new_pdf_files:
            try:
                paper = self.register_paper(pdf_path)
                if paper:
                    registered_papers.append(paper)
            except Exception as e:
                logger.error(f"Unexpected error registering {pdf_path.name}: {str(e)}")

        if registered_papers:
            logger.info(f"Registered {len(registered_papers)} new papers")
        
        return registered_papers

    def get_papers_for_processing(self, limit: Optional[int] = None) -> List[Paper]:
        """
        Get a list of papers that need to be processed.

        Args:
            limit: Optional maximum number of papers to return

        Returns:
            List of Paper objects to process
        """
        try:
            with db_session() as db:
                query = db.query(Paper).filter(Paper.processed_at.is_(None))
                
                if limit:
                    query = query.limit(limit)
                return query.all()
        except Exception as e:
            logger.error(f"Error getting papers for processing: {str(e)}")
            return []

    def mark_paper_processed(self, paper_id: int) -> bool:
        """
        Mark a paper as processed in the database.

        Args:
            paper_id: ID of the paper to mark as processed

        Returns:
            True if successful, False otherwise
        """
        try:
            with db_session() as db:
                paper = db.query(Paper).filter(Paper.id == paper_id).first()
                
                if not paper:
                    logger.warning(f"Paper not found with ID: {paper_id}")
                    return False
                    
                paper.mark_processed()
                logger.info(f"Marked paper as processed: {paper}")
                return True
                
        except Exception as e:
            logger.error(f"Error marking paper {paper_id} as processed: {str(e)}")
            return False


def main():
    """Run the paper ingestor as a standalone script."""
    print("Starting paper ingestor...")
    ingestor = PaperIngestor()
    new_papers = ingestor.process_new_papers()
    
    print(f"Registered {len(new_papers)} new papers:")
    for paper in new_papers:
        print(f"  - {paper}")
    
    unprocessed_papers = ingestor.get_papers_for_processing()
    print(f"\nFound {len(unprocessed_papers)} papers ready for processing:")
    for paper in unprocessed_papers:
        print(f"  - {paper}")


if __name__ == "__main__":
    main()
