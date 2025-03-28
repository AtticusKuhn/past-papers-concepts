"""
LLM integration utilities for the Past Paper Concept Analyzer.

This module provides functions for interacting with LLMs, including
formatting prompts, making API calls, and handling responses.
"""

import base64
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import openai

import config
from utils.logging_config import setup_logger

# Configure logger
logger = setup_logger(__name__, logging.INFO, "logs/llm.log")


class LLMProcessor:
    """
    Handles interactions with Large Language Models.
    
    This class abstracts the details of making API calls to LLMs, 
    handling rate limiting, formatting prompts, and processing responses.
    """
    
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize the LLM processor.
        
        Args:
            model: LLM model to use (defaults to config value)
            temperature: Temperature setting (defaults to config value)
            max_tokens: Maximum tokens to generate (defaults to config value)
            api_key: API key to use (defaults to config value)
        """
        self.model = model or config.OPENAI_MODEL
        self.temperature = temperature or config.OPENAI_TEMPERATURE
        self.max_tokens = max_tokens or config.OPENAI_MAX_TOKENS
        
        # Set API key
        api_key = api_key or config.OPENAI_API_KEY
        openai.api_key = api_key
        
        # Load default prompt templates
        self.prompt_templates = {}
        self._load_prompt_templates()
        
        logger.info(f"Initialized LLM processor with model: {self.model}")
    
    def _load_prompt_templates(self) -> None:
        """Load prompt templates from the prompts directory."""
        prompts_dir = config.PROMPTS_DIR
        
        if not prompts_dir.exists():
            logger.warning(f"Prompts directory not found: {prompts_dir}")
            return
        
        # Load all .md files in the prompts directory
        prompt_files = list(prompts_dir.glob("*.md"))
        
        for prompt_file in prompt_files:
            try:
                with open(prompt_file, "r", encoding="utf-8") as f:
                    prompt_text = f.read()
                
                # Use the filename (without extension) as the template name
                template_name = prompt_file.stem
                self.prompt_templates[template_name] = prompt_text
                logger.debug(f"Loaded prompt template: {template_name}")
            
            except Exception as e:
                logger.error(f"Error loading prompt template {prompt_file}: {str(e)}")
        
        logger.info(f"Loaded {len(self.prompt_templates)} prompt templates")
    
    def get_prompt_template(self, template_name: str) -> Optional[str]:
        """
        Get a prompt template by name.
        
        Args:
            template_name: Name of the template to retrieve
            
        Returns:
            Prompt template text or None if not found
        """
        if template_name in self.prompt_templates:
            return self.prompt_templates[template_name]
        
        logger.warning(f"Prompt template not found: {template_name}")
        return None
    
    def format_prompt(
        self, template_name: str, replacements: Dict[str, str]
    ) -> Optional[str]:
        """
        Format a prompt template with replacements.
        
        Args:
            template_name: Name of the template to format
            replacements: Dictionary of placeholder replacements
            
        Returns:
            Formatted prompt text or None if template not found
        """
        template = self.get_prompt_template(template_name)
        
        if not template:
            return None
        
        # Replace placeholders in the template
        formatted_prompt = template
        for key, value in replacements.items():
            placeholder = f"{{{key}}}"
            formatted_prompt = formatted_prompt.replace(placeholder, value)
        
        return formatted_prompt
    
    def extract_concepts_from_pdf(
        self, pdf_path: Path, prompt_template: str = "concept_extraction"
    ) -> List[Dict[str, Any]]:
        """
        Extract concepts directly from a PDF file using vision capabilities.
        
        Args:
            pdf_path: Path to the PDF file
            prompt_template: Name of the prompt template to use
            
        Returns:
            List of extracted concepts
        """
        logger.info(f"Processing PDF file: {pdf_path}")
        
        try:
            # Encode PDF as base64
            base64_pdf = self._encode_pdf_base64(pdf_path)
            
            # Get the prompt template
            prompt_text = self.get_prompt_template(prompt_template)
            if not prompt_text:
                logger.error(f"Prompt template not found: {prompt_template}")
                return []
            
            # Replace placeholders in the prompt
            prompt_text = prompt_text.replace("{text}", "in the attached PDF file")
            
            # Prepare message for vision model
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt_text,
                        },
                        {
                            "type": "file",
                            "file": {
                                "file_data": f"data:application/pdf;base64,{base64_pdf}",
                                "filename": pdf_path.name,
                            },
                        },
                    ],
                }
            ]
            
            logger.debug("Sending request to LLM with PDF attachment")
            
            # Call the API
            response = openai.chat.completions.create(
                model="gpt-4o",  # Use GPT-4o for vision capabilities
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            response_text = response.choices[0].message.content
            logger.debug(f"Received response of length: {len(response_text)}")
            
            # Extract and parse JSON from the response
            concepts = self._parse_concepts_from_response(response_text)
            logger.info(f"Extracted {len(concepts)} concepts from PDF")
            
            return concepts
            
        except Exception as e:
            logger.error(f"Error extracting concepts from PDF: {str(e)}")
            
            # Log detailed error information
            import traceback
            logger.error(f"Detailed error traceback: {traceback.format_exc()}")
            
            return []
    
    def _encode_pdf_base64(self, pdf_path: Path) -> str:
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
                base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
                logger.debug(f"Encoded PDF as base64 ({len(base64_pdf)} chars)")
                return base64_pdf
        except Exception as e:
            logger.error(f"Error encoding PDF as base64: {str(e)}")
            raise
    
    def _parse_concepts_from_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse concepts from the LLM response text.
        
        Args:
            response_text: Raw response text from the LLM
            
        Returns:
            List of parsed concept dictionaries
        """
        # Extract JSON from response using regex
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
                logger.warning("No JSON found in response. Using full response text.")
                json_str = response_text
        
        # Try to parse the JSON
        try:
            data = json.loads(json_str.strip())
            concepts = data.get("concepts", [])
            return concepts
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON: {str(e)}")
            logger.debug(f"Failed JSON string: {json_str[:500]}...")
            
            # Try a fallback approach
            try:
                # Fix common JSON issues - wrap with braces if needed
                if '"concepts"' in json_str and not json_str.strip().startswith("{"):
                    fixed_json = "{" + json_str + "}"
                    data = json.loads(fixed_json)
                    concepts = data.get("concepts", [])
                    logger.info("Successfully parsed JSON with fallback method")
                    return concepts
            except Exception:
                logger.error("Fallback JSON parsing also failed")
            
            return []

    def deduplicate_concepts(self, concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate concepts by name.
        
        Args:
            concepts: List of concept dictionaries
            
        Returns:
            Deduplicated list of concepts
        """
        concept_map = {}
        
        for concept in concepts:
            name = concept["name"].lower()
            
            if name in concept_map:
                existing = concept_map[name]
                
                # Keep highest confidence
                existing["confidence"] = max(
                    existing.get("confidence", 0.5), 
                    concept.get("confidence", 0.5)
                )
                
                # Combine contexts
                if "context" in concept and "context" in existing:
                    if existing["context"] != concept["context"]:
                        existing["context"] = f"{existing['context']}\n\n{concept['context']}"
                elif "context" in concept:
                    existing["context"] = concept["context"]
                
                # Combine related concepts
                if "related_concepts" in concept and "related_concepts" in existing:
                    existing_related = set(existing["related_concepts"])
                    new_related = set(concept["related_concepts"])
                    existing["related_concepts"] = list(existing_related.union(new_related))
                elif "related_concepts" in concept:
                    existing["related_concepts"] = concept["related_concepts"]
            else:
                concept_map[name] = concept
        
        logger.info(f"Deduplicated {len(concepts)} concepts to {len(concept_map)} unique concepts")
        return list(concept_map.values())
