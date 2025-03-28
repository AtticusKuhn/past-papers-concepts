"""
Text Analyzer for the Past Paper Concept Analyzer.

This module handles the analysis of PDF files using Large Language Models to
identify key concepts, extracts them, and stores them in the database.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import config
from models.base import db_session, init_db
from models.concept import Concept, ConceptRelation, Occurrence
from models.paper import Paper
from utils.llm import LLMProcessor
from utils.logging_config import setup_logger

# Configure logger with a dedicated log file
logger = setup_logger(__name__, logging.INFO, "logs/text_analyzer.log")


class TextAnalyzer:
    """
    Analyzes PDF files using Large Language Models to identify key concepts.

    This class is responsible for:
    1. Processing PDF files through LLM analysis
    2. Extracting, validating, and normalizing concepts
    3. Storing concepts in the database with proper relationships
    """

    def __init__(
        self,
        batch_size: Optional[int] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """
        Initialize the TextAnalyzer.

        Args:
            batch_size: Maximum number of papers to process in one batch
            model: LLM model to use (defaults to config value)
            temperature: Temperature setting (defaults to config value)
        """
        # Configuration
        self.pdf_dir = config.PDF_DIR
        self.batch_size = batch_size or config.RATE_LIMIT_BATCH_SIZE
        
        # Initialize LLM processor
        self.llm_processor = LLMProcessor(
            model=model,
            temperature=temperature,
        )
        
        logger.info(
            f"Initialized TextAnalyzer with model: {self.llm_processor.model}, "
            f"batch size: {self.batch_size}"
        )

    def get_pdf_path(self, paper: Paper) -> Path:
        """
        Get the path to the PDF file for a paper.

        Args:
            paper: Paper object

        Returns:
            Path to the PDF file
        """
        return self.pdf_dir / paper.filename

    def extract_concepts_from_paper(self, paper: Paper) -> List[Dict[str, Any]]:
        """
        Extract concepts from a paper's PDF file.

        Args:
            paper: Paper object

        Returns:
            List of extracted concepts
        """
        # Get PDF path
        pdf_path = self.get_pdf_path(paper)

        if not pdf_path.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            return []

        # Extract concepts from the PDF using the LLM processor
        logger.info(f"Processing PDF for {paper} using LLM")
        
        try:
            # Extract concepts using the LLM processor
            concepts = self.llm_processor.extract_concepts_from_pdf(
                pdf_path, prompt_template="concept_extraction"
            )
            
            # Deduplicate concepts
            unique_concepts = self.llm_processor.deduplicate_concepts(concepts)
            
            # Validate and normalize concepts
            validated_concepts = self._validate_and_normalize_concepts(unique_concepts)
            
            logger.info(f"Extracted {len(validated_concepts)} concepts from {paper}")
            return validated_concepts
            
        except Exception as e:
            logger.error(f"Error extracting concepts from {paper}: {str(e)}")
            # Log more detailed error information
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def _validate_and_normalize_concepts(
        self, concepts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Validate and normalize concepts from LLM.
        
        This ensures all concepts have required fields and consistent formatting.

        Args:
            concepts: List of concepts from LLM

        Returns:
            List of validated and normalized concepts
        """
        validated = []
        
        for i, concept in enumerate(concepts):
            try:
                # Check for required fields
                if "name" not in concept or not concept["name"]:
                    logger.warning(f"Concept {i+1} missing name field, skipping")
                    continue
                    
                # Normalize confidence value
                if "confidence" in concept:
                    try:
                        confidence = float(concept["confidence"])
                        # Ensure confidence is in range [0, 1]
                        concept["confidence"] = max(0.0, min(1.0, confidence))
                    except (ValueError, TypeError):
                        concept["confidence"] = 0.8  # Default confidence
                else:
                    concept["confidence"] = 0.8  # Default confidence
                
                # Ensure required fields exist with defaults if needed
                if "category" not in concept:
                    concept["category"] = None
                    
                if "description" not in concept:
                    concept["description"] = None
                    
                if "context" not in concept:
                    concept["context"] = None
                
                # Normalize related concepts
                if "related_concepts" not in concept:
                    concept["related_concepts"] = []
                elif not isinstance(concept["related_concepts"], list):
                    # Convert non-list to list
                    if isinstance(concept["related_concepts"], str):
                        concept["related_concepts"] = [concept["related_concepts"]]
                    else:
                        concept["related_concepts"] = []
                
                # Clean related concepts - remove empty strings and duplicates
                if concept["related_concepts"]:
                    related = [
                        name for name in concept["related_concepts"] 
                        if name and isinstance(name, str)
                    ]
                    concept["related_concepts"] = list(set(related))
                
                # Add to validated list
                validated.append(concept)
                
            except Exception as e:
                logger.error(f"Error validating concept {i+1}: {str(e)}")
                logger.debug(f"Problematic concept data: {concept}")
        
        logger.info(f"Validated {len(validated)} concepts out of {len(concepts)}")
        return validated

    def store_concept(
        self, concept_data: Dict[str, Any], paper: Paper, db
    ) -> Tuple[Optional[Concept], Optional[Occurrence]]:
        """
        Store a concept and its occurrence in the database.

        Args:
            concept_data: Concept data from LLM
            paper: Paper object
            db: Database session

        Returns:
            Tuple of (Concept, Occurrence) objects or (None, None) on error
        """
        try:
            # Extract key fields
            name = concept_data["name"]
            category = concept_data.get("category")
            description = concept_data.get("description")
            parent_concept_name = concept_data.get("parent_concept")
            
            # Check if concept already exists
            existing = db.query(Concept).filter(Concept.name == name).first()
            
            if existing:
                concept = existing
                
                # Update fields if needed and newer information is available
                if not concept.category and category:
                    concept.category = category
                    
                if not concept.description and description:
                    concept.description = description
                    
                # Handle parent concept if it doesn't already have one
                if not concept.parent_concept_id and parent_concept_name:
                    self._set_parent_concept(concept, parent_concept_name, db)
            else:
                # Create new concept
                concept = Concept(
                    name=name,
                    category=category,
                    description=description,
                )
                db.add(concept)
                
                # Handle parent concept 
                if parent_concept_name:
                    self._set_parent_concept(concept, parent_concept_name, db)
                
                # Need to flush to get the ID
                db.flush()
            
            # Create occurrence
            occurrence = Occurrence(
                concept_id=concept.id,
                paper_id=paper.id,
                question=self._extract_question_from_paper(paper),
                context=concept_data.get("context"),
                confidence=concept_data.get("confidence", 0.8),
            )
            db.add(occurrence)
            
            logger.debug(f"Stored concept: {concept.name} (ID: {concept.id})")
            return concept, occurrence
            
        except Exception as e:
            logger.error(f"Error storing concept {concept_data.get('name', 'unknown')}: {str(e)}")
            return None, None
    
    def _set_parent_concept(
        self, concept: Concept, parent_name: str, db
    ) -> None:
        """
        Set the parent concept for a concept.
        
        Args:
            concept: Concept to set parent for
            parent_name: Name of the parent concept
            db: Database session
        """
        if not parent_name or parent_name == concept.name:
            return
            
        # Find or create parent concept
        parent = db.query(Concept).filter(Concept.name == parent_name).first()
        
        if not parent:
            parent = Concept(name=parent_name)
            db.add(parent)
            db.flush()
            logger.debug(f"Created new parent concept: {parent_name} (ID: {parent.id})")
        
        # Set parent relation
        concept.parent_concept_id = parent.id
        logger.debug(f"Set parent relation: {concept.name} -> {parent_name}")
    
    def _extract_question_from_paper(self, paper: Paper) -> Optional[str]:
        """
        Extract question information from a paper.
        
        Args:
            paper: Paper object
            
        Returns:
            Question identifier or None
        """
        # The course field currently stores question information in the format "qXX"
        if paper.course and paper.course.startswith("q"):
            return paper.course
        return None

    def store_concept_relations(
        self, concept: Concept, related_names: List[str], db
    ) -> int:
        """
        Store relations between concepts in the database.

        Args:
            concept: Source concept
            related_names: List of related concept names
            db: Database session

        Returns:
            Number of relations created
        """
        if not related_names:
            return 0
            
        relations_created = 0
        
        for related_name in related_names:
            try:
                # Skip empty names or self-relations
                if not related_name or related_name == concept.name:
                    continue
    
                # Find or create related concept
                related = db.query(Concept).filter(Concept.name == related_name).first()
                if not related:
                    related = Concept(name=related_name)
                    db.add(related)
                    db.flush()
    
                # Check if relation already exists
                existing = (
                    db.query(ConceptRelation)
                    .filter(
                        ConceptRelation.concept1_id == concept.id,
                        ConceptRelation.concept2_id == related.id,
                    )
                    .first()
                )
    
                if not existing:
                    # Create new relation
                    relation = ConceptRelation(
                        concept1_id=concept.id,
                        concept2_id=related.id,
                        relation_type="related",
                    )
                    db.add(relation)
                    relations_created += 1
            except Exception as e:
                logger.error(f"Error creating relation {concept.name} -> {related_name}: {str(e)}")
        
        return relations_created

    def process_and_store_concepts(self, paper: Paper) -> int:
        """
        Process a paper and store extracted concepts in the database.

        Args:
            paper: Paper to process

        Returns:
            Number of concepts stored
        """
        # Extract concepts
        try:
            logger.info(f"Extracting concepts from {paper}")
            concepts_data = self.extract_concepts_from_paper(paper)
            
            if not concepts_data:
                logger.warning(f"No concepts extracted from {paper}")
                return 0
                
            logger.info(f"Extracted {len(concepts_data)} concepts from {paper}")
            
            # Log sample concept for debugging
            if logger.isEnabledFor(logging.DEBUG) and concepts_data:
                sample = json.dumps(concepts_data[0], indent=2)
                logger.debug(f"Sample concept: {sample[:300]}...")
                
        except Exception as e:
            logger.error(f"Error during concept extraction for {paper}: {str(e)}")
            return 0

        # Store concepts in database
        stored_count = 0
        
        logger.info(f"Storing {len(concepts_data)} concepts for {paper}")
        
        try:
            with db_session() as db:
                for i, concept_data in enumerate(concepts_data):
                    try:
                        # Store concept and occurrence
                        result = self.store_concept(concept_data, paper, db)
                        concept, occurrence = result
                        
                        if not concept or not occurrence:
                            logger.warning(
                                f"Failed to store concept {i+1}/{len(concepts_data)}: "
                                f"{concept_data.get('name', 'unknown')}"
                            )
                            continue
                        
                        # Store relations
                        related_names = concept_data.get("related_concepts", [])
                        if related_names:
                            relation_count = self.store_concept_relations(
                                concept, related_names, db
                            )
                            logger.debug(
                                f"Created {relation_count} relations for concept: {concept.name}"
                            )
                        
                        stored_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing concept {i+1}: {str(e)}")
                        continue
                
                logger.info(f"Successfully stored {stored_count} concepts for {paper}")
                
        except Exception as e:
            logger.error(f"Database error while storing concepts: {str(e)}")
            
        return stored_count


def analyze_papers(limit: Optional[int] = None) -> int:
    """
    Process and analyze papers.
    
    Args:
        limit: Optional maximum number of papers to process
        
    Returns:
        Number of successfully processed papers
    """
    # Initialize database
    init_db()

    # Get papers to process
    from paper_ingestor import PaperIngestor

    ingestor = PaperIngestor()
    batch_size = limit or config.RATE_LIMIT_BATCH_SIZE
    papers = ingestor.get_papers_for_processing(limit=batch_size)

    if not papers:
        logger.info("No papers to process")
        return 0

    # Process each paper
    analyzer = TextAnalyzer()
    processed_count = 0
    
    for paper in papers:
        logger.info(f"Processing {paper}...")

        try:
            # Check if PDF file exists
            pdf_path = analyzer.get_pdf_path(paper)
            if not pdf_path.exists():
                logger.error(f"PDF file not found: {pdf_path}, skipping")
                continue

            # Process and store concepts
            concept_count = analyzer.process_and_store_concepts(paper)
            
            if concept_count > 0:
                # Mark paper as processed
                if ingestor.mark_paper_processed(paper.id):
                    logger.info(f"Marked {paper} as processed with {concept_count} concepts")
                    processed_count += 1
                else:
                    logger.error(f"Failed to mark {paper} as processed")
            else:
                logger.warning(f"No concepts stored for {paper}, not marking as processed")
                
        except Exception as e:
            logger.error(f"Error processing paper {paper}: {str(e)}")
            
            # Log detailed error information
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    logger.info(f"Successfully processed {processed_count} out of {len(papers)} papers")
    return processed_count


def main():
    """Run the text analyzer as a standalone script."""
    print("Starting text analyzer...")
    processed_count = analyze_papers()
    print(f"Processing complete. Processed {processed_count} papers.")


if __name__ == "__main__":
    main()
