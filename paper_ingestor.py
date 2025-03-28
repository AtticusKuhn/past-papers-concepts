"""
Paper Ingestor for the Past Paper Concept Analyzer.

This module handles the discovery, validation, and registration of PDF papers.
It monitors the pdfs/ directory and processes new files as they are added.
"""

import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple

from sqlalchemy.exc import IntegrityError

import config
from models.base import get_db, init_db
from models.paper import Paper

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PaperIngestor:
    """
    Handles the ingestion of PDF papers into the system.

    This class is responsible for:
    1. Discovering PDF files in the pdfs/ directory
    2. Extracting metadata from filenames or content
    3. Registering papers in the database
    4. Triggering the processing pipeline
    """

    # Regex pattern for extracting metadata from filenames
    # Format: YEAR-pXX-qYY-solutions.pdf (e.g., 2021-p07-q08-solutions.pdf)
    FILENAME_PATTERN = re.compile(r"(\d{4})-p(\d{2})-q(\d{2})-solutions\.pdf", re.IGNORECASE)

    def __init__(self):
        """Initialize the PaperIngestor."""
        # Ensure database tables exist
        init_db()
        self.pdf_dir = config.PDF_DIR

    def find_new_papers(self) -> List[Path]:
        """
        Find PDF files in the pdfs/ directory that haven't been processed.

        Returns:
            List of Path objects for unprocessed PDF files
        """
        # Get list of PDF files
        pdf_files = list(self.pdf_dir.glob("*.pdf"))

        # Get list of already processed filenames from database
        with next(get_db()) as db:
            existing_filenames = {
                paper.filename for paper in db.query(Paper.filename).all()
            }

        # Filter to only new files
        new_files = [pdf for pdf in pdf_files if pdf.name not in existing_filenames]
        logger.info(f"Found {len(new_files)} new papers to process")

        return new_files

    def extract_metadata(
        self, pdf_path: Path
    ) -> Tuple[Optional[int], Optional[str], Optional[int]]:
        """
        Extract metadata (year, paper number, question number) from a PDF filename.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Tuple of (year, course, paper_number) or (None, None, None) if extraction fails
            Note: For the new format, 'course' field stores question information
        """
        filename = pdf_path.name
        match = self.FILENAME_PATTERN.match(filename)

        if match:
            year = int(match.group(1))
            paper_number = int(match.group(2))
            question_number = int(match.group(3))
            # Using question number as the course for compatibility with existing code
            course = f"q{question_number}"
            return year, course, paper_number
        else:
            logger.warning(f"Could not extract metadata from filename: {filename}")
            # TODO: Implement content-based metadata extraction as fallback
            return None, None, None

    def register_paper(self, pdf_path: Path) -> Optional[Paper]:
        """
        Register a paper in the database.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Registered Paper object or None if registration fails
        """
        year, course, paper_number = self.extract_metadata(pdf_path)

        if not all([year, course, paper_number]):
            logger.error(f"Missing metadata for {pdf_path.name}, skipping registration")
            return None

        # Create new Paper object
        new_paper = Paper(
            year=year, course=course, paper_number=paper_number, filename=pdf_path.name
        )

        # Add to database
        try:
            with next(get_db()) as db:
                db.add(new_paper)
                db.commit()
                db.refresh(new_paper)
                logger.info(f"Registered paper: {new_paper}")
                return new_paper
        except IntegrityError:
            logger.warning(f"Paper already exists in database: {pdf_path.name}")
            return None
        except Exception as e:
            logger.error(f"Error registering paper: {e}")
            return None

    def process_new_papers(self) -> List[Paper]:
        """
        Find and register all new papers.

        Returns:
            List of registered Paper objects
        """
        new_pdf_files = self.find_new_papers()
        registered_papers = []

        for pdf_path in new_pdf_files:
            paper = self.register_paper(pdf_path)
            if paper:
                registered_papers.append(paper)

        logger.info(f"Registered {len(registered_papers)} new papers")
        return registered_papers

    def get_papers_for_processing(self, limit: int = None) -> List[Paper]:
        """
        Get a list of papers that need to be processed.

        Args:
            limit: Optional maximum number of papers to return

        Returns:
            List of Paper objects to process
        """
        with next(get_db()) as db:
            query = db.query(Paper).filter(Paper.processed_at.is_(None))
            if limit:
                query = query.limit(limit)
            return query.all()

    def mark_paper_processed(self, paper_id: int) -> bool:
        """
        Mark a paper as processed in the database.

        Args:
            paper_id: ID of the paper to mark as processed

        Returns:
            True if successful, False otherwise
        """
        try:
            with next(get_db()) as db:
                paper = db.query(Paper).filter(Paper.id == paper_id).first()
                if paper:
                    paper.mark_processed()
                    db.commit()
                    logger.info(f"Marked paper as processed: {paper}")
                    return True
                else:
                    logger.warning(f"Paper not found with ID: {paper_id}")
                    return False
        except Exception as e:
            logger.error(f"Error marking paper as processed: {e}")
            return False


def main():
    """Run the paper ingestor as a standalone script."""
    ingestor = PaperIngestor()
    new_papers = ingestor.process_new_papers()
    print(f"Registered {len(new_papers)} new papers:")
    for paper in new_papers:
        print(f"  - {paper}")


if __name__ == "__main__":
    main()
