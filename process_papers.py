#!/usr/bin/env python
"""
Main processing script for the Past Paper Concept Analyzer.

This script ties together all components of the pipeline and provides
a simple CLI interface for running the processing pipeline.
"""

import argparse
import logging
import sys
from typing import List, Optional

from models.base import init_db
from paper_ingestor import PaperIngestor
from text_analyzer import TextAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("processing.log")],
)
logger = logging.getLogger(__name__)


def run_pipeline(limit: Optional[int] = None, steps: List[str] = None):
    """
    Run the complete processing pipeline or specific steps.

    Args:
        limit: Optional maximum number of papers to process
        steps: Optional list of steps to run ('ingest', 'analyze')
    """
    # Default to all steps if none specified
    if not steps:
        steps = ["ingest", "analyze"]

    logger.info(f"Starting pipeline with steps: {', '.join(steps)}")

    # Initialize database
    init_db()

    # Step 1: Ingest papers
    if "ingest" in steps:
        logger.info("Step 1: Ingesting papers")
        ingestor = PaperIngestor()
        papers = ingestor.process_new_papers()
        logger.info(f"Ingested {len(papers)} new papers")

    # Get unprocessed papers for next steps
    ingestor = PaperIngestor()
    papers_to_process = ingestor.get_papers_for_processing(limit=limit)
    logger.info(f"Found {len(papers_to_process)} papers to process")

    if not papers_to_process:
        logger.info("No papers to process, pipeline complete")
        return

    # Step 2: Analyze PDFs and extract concepts
    if "analyze" in steps:
        logger.info("Step 2: Analyzing PDFs directly with GPT-4o")
        analyzer = TextAnalyzer()

        for paper in papers_to_process:
            logger.info(f"Analyzing {paper}")

            try:
                # Check if PDF file exists
                pdf_path = analyzer.get_pdf_path(paper)
                if not pdf_path.exists():
                    logger.warning(f"PDF file not found: {pdf_path}, skipping")
                    continue

                # Process and store concepts
                logger.info(f"Starting concept extraction for {paper}")
                try:
                    concept_count = analyzer.process_and_store_concepts(paper)
                    
                    if concept_count > 0:
                        logger.info(f"Extracted {concept_count} concepts from {paper}")
                        ingestor.mark_paper_processed(paper.id)
                    else:
                        logger.warning(f"No concepts extracted from {paper}")
                        
                except Exception as inner_e:
                    # Get detailed exception info
                    import traceback
                    import sys
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
                    
                    # Log the full traceback
                    logger.error(f"Error in process_and_store_concepts for {paper}:")
                    for line in tb_lines:
                        logger.error(line.rstrip())
                    
                    # Examine the response if it's a JSON decoding error
                    if "JSONDecodeError" in str(inner_e):
                        logger.error(f"JSON parsing error. Raw exception: {repr(inner_e)}")
                        logger.error(f"Error message content: {str(inner_e)}")
                    
                    raise inner_e

            except Exception as e:
                # Log detailed information about the exception
                logger.error(f"Error analyzing {paper}: {e}")
                
                # Add detailed traceback
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")

    logger.info("Pipeline complete!")


def main():
    """Parse command line arguments and run the pipeline."""
    parser = argparse.ArgumentParser(
        description="Process past papers and extract concepts"
    )

    parser.add_argument(
        "--steps",
        choices=["ingest", "analyze"],
        nargs="+",
        help="Specific steps to run (default: all steps)",
    )

    parser.add_argument("--limit", type=int, help="Maximum number of papers to process")

    args = parser.parse_args()

    try:
        run_pipeline(limit=args.limit, steps=args.steps)
    except Exception as e:
        logger.error(f"Error running pipeline: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
