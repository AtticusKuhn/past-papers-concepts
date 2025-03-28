"""
Text Analyzer for the Past Paper Concept Analyzer.

This module handles the analysis of PDFs using LLMs to identify key concepts.
It processes PDF files directly through GPT-4o's vision capabilities,
and stores the extracted concepts in the database.
"""

import json
import logging
import re
import time
import base64
from pathlib import Path
from typing import Any, Dict, List, Tuple

import openai
from langchain_community.chat_models import ChatOpenAI
# LangChain imports
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from langchain.text_splitter import RecursiveCharacterTextSplitter

import config
from models.base import get_db, init_db
from models.concept import Concept, ConceptRelation, Occurrence
from models.paper import Paper

# Configure logging
logging.basicConfig(
    level=0,  # Changed from INFO to DEBUG to see more detailed logs
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("text_analyzer_debug.log")  # Separate log file for debugging
    ]
)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai.api_key = config.OPENAI_API_KEY


class TextAnalyzer:
    """
    Analyzes PDF files directly using GPT-4o to identify key concepts.

    This class is responsible for:
    1. Processing PDF files directly through GPT-4o
    2. Parsing responses to extract concepts
    3. Storing concepts in the database
    """

    def __init__(self, batch_size: int = None):
        """
        Initialize the TextAnalyzer.

        Args:
            batch_size: Optional override for batch size (default from config)
        """
        self.pdf_dir = config.PDF_DIR
        self.prompts_dir = config.PROMPTS_DIR

        # Rate limiting and batching
        self.batch_size = batch_size or config.RATE_LIMIT_BATCH_SIZE

        # Load prompt template
        self._load_prompt_template()


    def _load_prompt_template(self):
        """Load the concept extraction prompt template."""
        prompt_path = self.prompts_dir / "concept_extraction.md"

        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt template not found: {prompt_path}")

        with open(prompt_path, "r", encoding="utf-8") as file:
            self.prompt_text = file.read()

        logger.info(f"Loaded prompt template from {prompt_path}")

    def get_pdf_path(self, paper: Paper) -> Path:
        """
        Get the path to the PDF file for a paper.

        Args:
            paper: Paper object

        Returns:
            Path to the PDF file
        """
        return self.pdf_dir / paper.filename

    def encode_pdf_base64(self, pdf_path: Path) -> str:
        """
        Encode a PDF file as base64.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Base64-encoded PDF content
        """
        try:
            with open(pdf_path, "rb") as pdf_file:
                pdf_bytes = pdf_file.read()
                base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                logger.info(f"Encoded PDF {pdf_path} as base64 ({len(base64_pdf)} chars)")
                return base64_pdf
        except Exception as e:
            logger.error(f"Error encoding PDF as base64: {e}")
            raise
    
    def extract_concepts_from_pdf(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """
        Extract concepts directly from a PDF file using GPT-4o.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of extracted concepts
        """
        logger.info(f"Processing PDF file: {pdf_path}")
        
        # Encode PDF as base64
        try:
            base64_pdf = self.encode_pdf_base64(pdf_path)
        except Exception as e:
            logger.error(f"Failed to encode PDF {pdf_path}: {e}")
            return []
        
        # Prepare message for GPT-4o with PDF attachment
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": self.prompt_text.replace("{text}", "in the attached PDF file")
                    },
                    {
                        "type": "file",
                        "file": {
                            "file_data": f"data:application/pdf;base64,{base64_pdf}",
                            "filename": pdf_path.name
                        }
                    }
                ]
            }
        ]
        
        logger.debug(f"Sending GPT-4o request with PDF attachment...")
        
        try:
            # Use direct OpenAI API call for GPT-4o with the PDF
            # Using the OpenAI v1.0+ API format
            response = openai.chat.completions.create(
                model="gpt-4o",  # Use GPT-4o for vision capabilities
                messages=messages,
                temperature=config.OPENAI_TEMPERATURE,
                max_tokens=config.OPENAI_MAX_TOKENS
            )
            
            response_text = response.choices[0].message.content
            
            # Log the raw response for debugging
            logger.debug(f"Raw GPT-4o response: {response_text}")
            
            # Extract JSON from response
            # The LLM might include explanatory text before/after the JSON
            json_match = re.search(r"```json\s*(.+?)\s*```", response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                logger.debug(f"Found JSON in code block: {json_str[:100]}...")
            else:
                # Try to find just a JSON object if not wrapped in code blocks
                json_match = re.search(r"(\{.*\})", response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                    logger.debug(f"Found JSON object using regex: {json_str[:100]}...")
                else:
                    json_str = response_text
                    logger.debug(f"Using full response as JSON: {json_str[:100]}...")
            
            # Check if the JSON string appears valid before parsing
            json_str = json_str.strip()
            if not (json_str.startswith('{') and json_str.endswith('}')):
                logger.warning(f"JSON string doesn't appear to be a valid object. First 100 chars: {json_str[:100]}")
            
            # Parse JSON response
            try:
                # Log the exact string we're trying to parse
                logger.debug(f"Attempting to parse JSON string: {json_str[:100]}...")
                
                # Check for common JSON formatting issues
                if json_str.startswith('\n'):
                    logger.warning("JSON string starts with newline, attempting to clean")
                    json_str = json_str.strip()
                
                data = json.loads(json_str)
                concepts = data.get("concepts", [])
                logger.info(f"Extracted {len(concepts)} concepts from chunk")
                return concepts
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing LLM response as JSON: {e}")
                logger.error(f"Failed JSON: {json_str}")
                logger.error(f"Response: {response_text}")
                
                # Try a fallback approach - attempt to fix common JSON issues
                logger.info("Attempting fallback JSON parsing...")
                try:
                    # Fix for partial JSON containing only "concepts": [...]
                    if '"concepts"' in json_str and not json_str.strip().startswith('{'):
                        fixed_json = '{' + json_str + '}'
                        logger.debug(f"Attempting to fix JSON by wrapping in braces: {fixed_json[:100]}...")
                        data = json.loads(fixed_json)
                        concepts = data.get("concepts", [])
                        logger.info(f"Fallback successful! Extracted {len(concepts)} concepts from chunk")
                        return concepts
                except Exception as fallback_error:
                    logger.error(f"Fallback JSON parsing also failed: {fallback_error}")
                
                return []

        except Exception as e:
            logger.error(f"Error extracting concepts: {e}")
            
            # Get more detailed error information
            import traceback
            logger.error(f"Detailed error traceback: {traceback.format_exc()}")
            
            # Check for specific OpenAI errors
            if "openai" in str(e).lower() or "httpstatuser" in str(e).lower():
                logger.error(
                    "This appears to be an OpenAI API error. "
                    "If it's a 400 Bad Request, you may be exceeding token limits. "
                    "Try reducing the document size or enabling chunking."
                )
            
            return []

    def extract_concepts_from_paper(self, paper: Paper) -> List[Dict[str, Any]]:
        """
        Extract concepts directly from a paper's PDF file.

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
        
        # Extract concepts directly from the PDF
        logger.info(f"Processing PDF for {paper} using GPT-4o directly")
        all_concepts = self.extract_concepts_from_pdf(pdf_path)
        
        # No need to deduplicate since we're not combining chunks,
        # but we'll keep the function call for consistency in case
        # the LLM returns duplicates internally
        unique_concepts = self._deduplicate_concepts(all_concepts)

        logger.info(f"Extracted {len(unique_concepts)} unique concepts from {paper}")
        return unique_concepts

    def _deduplicate_concepts(
        self, concepts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Deduplicate concepts by name.

        If the same concept appears multiple times, combine them keeping the
        highest confidence and all contexts.

        Args:
            concepts: List of concepts to deduplicate

        Returns:
            List of deduplicated concepts
        """
        concept_map = {}

        for concept in concepts:
            name = concept["name"].lower()

            if name in concept_map:
                existing = concept_map[name]

                # Keep highest confidence
                existing["confidence"] = max(
                    existing["confidence"], concept["confidence"]
                )

                # Combine contexts
                if existing["context"] != concept["context"]:
                    existing["context"] = (
                        f"{existing['context']}\n\n{concept['context']}"
                    )

                # Combine related concepts
                existing_related = set(existing["related_concepts"])
                new_related = set(concept["related_concepts"])
                existing["related_concepts"] = list(existing_related.union(new_related))
            else:
                concept_map[name] = concept

        return list(concept_map.values())

    def store_concept(
        self, concept_data: Dict[str, Any], paper: Paper, db
    ) -> Tuple[Concept, Occurrence]:
        """
        Store a concept and its occurrence in the database.

        Args:
            concept_data: Concept data from LLM
            paper: Paper object
            db: Database session

        Returns:
            Tuple of (Concept, Occurrence) objects
        """
        # Check if concept already exists
        name = concept_data["name"]
        existing = db.query(Concept).filter(Concept.name == name).first()

        if existing:
            concept = existing
            # Update fields if needed
            if not concept.category and concept_data.get("category"):
                concept.category = concept_data["category"]
            if not concept.description and concept_data.get("description"):
                concept.description = concept_data["description"]
        else:
            # Create new concept
            concept = Concept(
                name=name,
                category=concept_data.get("category"),
                description=concept_data.get("description"),
            )
            db.add(concept)
            # Need to flush to get the ID
            db.flush()

        # Create occurrence
        occurrence = Occurrence(
            concept_id=concept.id,
            paper_id=paper.id,
            question=None,  # TODO: Extract question number if available
            context=concept_data.get("context"),
            confidence=concept_data.get("confidence", 1.0),
        )
        db.add(occurrence)

        return concept, occurrence

    def store_concept_relations(
        self, concept: Concept, related_names: List[str], db
    ) -> List[ConceptRelation]:
        """
        Store relations between concepts in the database.

        Args:
            concept: Source concept
            related_names: List of related concept names
            db: Database session

        Returns:
            List of created ConceptRelation objects
        """
        relations = []

        for related_name in related_names:
            # Skip empty names
            if not related_name:
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
                relations.append(relation)

        return relations

    def process_and_store_concepts(self, paper: Paper) -> int:
        """
        Process a paper and store extracted concepts in the database.

        Args:
            paper: Paper to process

        Returns:
            Number of concepts stored
        """
        # Extract concepts
        logger.info(f"Extracting concepts from {paper}")
        try:
            concepts_data = self.extract_concepts_from_paper(paper)
            logger.info(f"Got {len(concepts_data)} raw concepts from {paper}")
            
            # Log sample of the first concept for debugging
            if concepts_data:
                sample_concept = concepts_data[0]
                logger.debug(f"Sample concept: {json.dumps(sample_concept, indent=2)[:200]}...")
            
            if not concepts_data:
                logger.warning(f"No concepts extracted from {paper}")
                return 0
                
        except Exception as e:
            logger.error(f"Error during concept extraction for {paper}: {e}")
            # Log the exception traceback for detailed debugging
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return 0

        # Store concepts in database
        stored_count = 0
        
        logger.info(f"Storing {len(concepts_data)} concepts for {paper}")
        
        with next(get_db()) as db:
            for i, concept_data in enumerate(concepts_data):
                try:
                    # Validate concept data before processing
                    required_fields = ["name"]
                    for field in required_fields:
                        if field not in concept_data:
                            logger.error(f"Missing required field '{field}' in concept data: {concept_data}")
                            continue
                    
                    logger.debug(f"Processing concept {i+1}/{len(concepts_data)}: {concept_data.get('name')}")
                    
                    # Store concept and occurrence
                    concept, occurrence = self.store_concept(concept_data, paper, db)
                    
                    # Log successful storage
                    logger.debug(f"Stored concept: {concept.name} (ID: {concept.id})")

                    # Store relations
                    if concept_data.get("related_concepts"):
                        logger.debug(f"Processing {len(concept_data['related_concepts'])} related concepts")
                        relations = self.store_concept_relations(
                            concept, concept_data["related_concepts"], db
                        )
                        logger.debug(f"Stored {len(relations)} concept relations")

                    # Store parent relation if specified
                    if concept_data.get("parent_concept"):
                        parent_name = concept_data["parent_concept"]
                        logger.debug(f"Processing parent concept: {parent_name}")
                        
                        parent = (
                            db.query(Concept)
                            .filter(Concept.name == parent_name)
                            .first()
                        )

                        if not parent:
                            parent = Concept(name=parent_name)
                            db.add(parent)
                            db.flush()
                            logger.debug(f"Created new parent concept: {parent_name} (ID: {parent.id})")

                        concept.parent_concept_id = parent.id
                        logger.debug(f"Set parent relation: {concept.name} -> {parent_name}")

                    stored_count += 1
                except Exception as e:
                    logger.error(f"Error storing concept {i+1}/{len(concepts_data)}: {e}")
                    # Include the concept data in the error log
                    logger.error(f"Failed concept data: {concept_data}")
                    # Log the exception traceback for detailed debugging
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    db.rollback()
                    continue

            # Commit all changes
            try:
                db.commit()
                logger.info(f"Successfully committed {stored_count} concepts to database")
            except Exception as e:
                logger.error(f"Error committing concepts to database: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                db.rollback()
                return 0

        logger.info(f"Stored {stored_count} concepts for {paper}")
        return stored_count


def main():
    """Run the text analyzer as a standalone script."""
    # Initialize database
    init_db()

    # Get papers to process
    from paper_ingestor import PaperIngestor

    ingestor = PaperIngestor()
    papers = ingestor.get_papers_for_processing(limit=config.RATE_LIMIT_BATCH_SIZE)

    if not papers:
        print("No papers to process.")
        return

    # Process each paper
    analyzer = TextAnalyzer()
    for paper in papers:
        print(f"Processing {paper}...")

        try:
            # Check if PDF file exists
            pdf_path = analyzer.get_pdf_path(paper)
            if not pdf_path.exists():
                print(f"  PDF file not found: {pdf_path}, skipping.")
                continue

            # Process and store concepts
            concept_count = analyzer.process_and_store_concepts(paper)
            print(f"  Stored {concept_count} concepts.")

            # Mark paper as processed
            if concept_count > 0:
                ingestor.mark_paper_processed(paper.id)
                print("  Marked as processed.")
        except Exception as e:
            print(f"  Error processing paper: {e}")


if __name__ == "__main__":
    main()
