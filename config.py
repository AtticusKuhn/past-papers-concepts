"""
Configuration management for the Past Paper Concept Analyzer.

This module handles loading environment variables, setting defaults,
and providing configuration values to other modules in the application.
"""

import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project directories
BASE_DIR = Path(__file__).resolve().parent
PDF_DIR = BASE_DIR / "pdfs"
EXTRACTED_DIR = BASE_DIR / "extracted"
DB_DIR = BASE_DIR / "db"
PROMPTS_DIR = BASE_DIR / "prompts"

# Ensure directories exist
PDF_DIR.mkdir(exist_ok=True)
EXTRACTED_DIR.mkdir(exist_ok=True)
DB_DIR.mkdir(exist_ok=True)
PROMPTS_DIR.mkdir(exist_ok=True)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_DIR}/concepts.db")

# LLM configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "8192"))
OPENAI_TEMPERATURE = float(
    os.getenv("OPENAI_TEMPERATURE", "0.0")
)  # Lower for more deterministic results

# Chunking configuration
MAX_CHUNK_SIZE = int(os.getenv("MAX_CHUNK_SIZE", "4000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# Rate limiting
RATE_LIMIT_CALLS = int(os.getenv("RATE_LIMIT_CALLS", "20"))  # Calls per minute
RATE_LIMIT_BATCH_SIZE = int(
    os.getenv("RATE_LIMIT_BATCH_SIZE", "5")
)  # Papers to process in one batch

# PDF processing
OCR_ENABLED = os.getenv("OCR_ENABLED", "false").lower() == "true"
TESSERACT_PATH = os.getenv(
    "TESSERACT_PATH", ""
)  # Path to Tesseract executable if using OCR


def get_config() -> Dict[str, Any]:
    """Return the current configuration as a dictionary."""
    return {
        "pdf_dir": str(PDF_DIR),
        "extracted_dir": str(EXTRACTED_DIR),
        "db_dir": str(DB_DIR),
        "prompts_dir": str(PROMPTS_DIR),
        "database_url": DATABASE_URL,
        "llm_provider": LLM_PROVIDER,
        "openai_model": OPENAI_MODEL,
        "openai_max_tokens": OPENAI_MAX_TOKENS,
        "openai_temperature": OPENAI_TEMPERATURE,
        "max_chunk_size": MAX_CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "rate_limit_calls": RATE_LIMIT_CALLS,
        "rate_limit_batch_size": RATE_LIMIT_BATCH_SIZE,
        "ocr_enabled": OCR_ENABLED,
        "tesseract_path": TESSERACT_PATH,
    }
