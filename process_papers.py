#!/usr/bin/env python
"""
Main processing script for the Past Paper Concept Analyzer.

This script ties together all components of the pipeline and provides
a simple CLI interface for running the processing pipeline.
"""

import argparse
import logging
import sys
import time
from typing import List, Optional

import config
from models.base import init_db
from paper_ingestor import PaperIngestor
# from pdf_processor import process_papers as process_pdf_papers
from text_analyzer import analyze_papers
from utils.logging_config import setup_logger

# Configure logger
logger = setup_logger(
    __name__, 
    logging.INFO, 
    "logs/process_papers.log"
)


def run_pipeline(
    limit: Optional[int] = None, 
    steps: Optional[List[str]] = None,
    pdf_only: bool = False,
    skip_extraction: bool = False,
):
    """
    Run the complete processing pipeline or specific steps.

    Args:
        limit: Optional maximum number of papers to process
        steps: Optional list of steps to run ('ingest', 'extract', 'analyze')
        pdf_only: Only process PDFs without analyzing them
        skip_extraction: Skip PDF text extraction, only run LLM analysis
    """
    # Default to all steps if none specified
    if not steps:
        steps = ["ingest", "extract", "analyze"]

    logger.info(f"Starting pipeline with steps: {', '.join(steps)}")
    start_time = time.time()

    # Initialize database
    init_db()

    # Step 1: Ingest papers
    if "ingest" in steps:
        logger.info("Step 1: Discovering and registering new papers")
        try:
            ingestor = PaperIngestor()
            papers = ingestor.process_new_papers()
            logger.info(f"Registered {len(papers)} new papers")
            
            # Display the registered papers
            if papers:
                for paper in papers:
                    logger.info(f"  - {paper}")
        except Exception as e:
            logger.error(f"Error during paper ingestion: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    # Get unprocessed papers for next steps
    try:
        ingestor = PaperIngestor()
        papers_to_process = ingestor.get_papers_for_processing(limit=limit)
        
        if not papers_to_process:
            logger.info("No papers to process, pipeline complete")
            end_time = time.time()
            logger.info(f"Pipeline completed in {end_time - start_time:.2f} seconds")
            return
            
        logger.info(f"Found {len(papers_to_process)} papers to process")
    except Exception as e:
        logger.error(f"Error retrieving papers for processing: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return

    # Analyze PDFs and extract concepts
    if "analyze" in steps:
        logger.info("Analyzing PDFs with LLM to extract concepts")
        try:
            processed_papers = analyze_papers(limit=limit)
            logger.info(f"Successfully analyzed {processed_papers} papers")
        except Exception as e:
            logger.error(f"Error during concept analysis: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    # Report completion
    end_time = time.time()
    logger.info(f"Pipeline completed in {end_time - start_time:.2f} seconds")


def main():
    """Parse command line arguments and run the pipeline."""
    parser = argparse.ArgumentParser(
        description="Process past papers and extract concepts"
    )

    parser.add_argument(
        "--steps",
        choices=["ingest", "extract", "analyze"],
        nargs="+",
        help="Specific steps to run (default: all steps)",
    )

    parser.add_argument(
        "--limit", 
        type=int, 
        help="Maximum number of papers to process"
    )
    
    parser.add_argument(
        "--pdf-only",
        action="store_true",
        help="Only process PDFs without analyzing them"
    )
    
    parser.add_argument(
        "--skip-extraction",
        action="store_true",
        help="Skip PDF text extraction, only run analysis"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.pdf_only and args.skip_extraction:
        print("Error: Cannot specify both --pdf-only and --skip-extraction")
        sys.exit(1)
    
    if args.pdf_only and args.steps and "analyze" in args.steps:
        print("Warning: --pdf-only flag will override 'analyze' step")
    
    if args.skip_extraction and args.steps and "extract" in args.steps:
        print("Warning: --skip-extraction flag will override 'extract' step")

    print(f"Starting Past Paper Concept Analyzer pipeline...")
    
    try:
        run_pipeline(
            limit=args.limit, 
            steps=args.steps,
            pdf_only=args.pdf_only,
            skip_extraction=args.skip_extraction
        )
        print("Processing complete!")
    except Exception as e:
        logger.error(f"Unhandled error in pipeline: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
