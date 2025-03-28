"""
Configuration management for the Past Paper Concept Analyzer.

This module provides a structured approach to configuration management,
including loading from environment variables, validation, and accessing
configuration values.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, cast

from dotenv import load_dotenv

from utils.logging_config import setup_logger

# Configure logger
logger = setup_logger(__name__, logging.INFO)

# Type variable for Config singleton
T = TypeVar('T', bound='Config')


class Config:
    """
    Configuration manager for the Past Paper Concept Analyzer.
    
    This class handles loading environment variables, setting up directories,
    and providing access to configuration values with proper typing.
    """
    
    # Singleton instance
    _instance: Optional['Config'] = None
    
    # Whether the config has been initialized
    _initialized: bool = False
    
    def __new__(cls: Type[T]) -> T:
        """Ensure Config is a singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        """Initialize the configuration (only once)."""
        if self._initialized:
            return
            
        # Load environment variables
        load_dotenv()
        
        # Set up directories
        self.BASE_DIR = Path(__file__).resolve().parent
        self.PDF_DIR = self.BASE_DIR / "pdfs"
        self.EXTRACTED_DIR = self.BASE_DIR / "extracted"
        self.DB_DIR = self.BASE_DIR / "db"
        self.PROMPTS_DIR = self.BASE_DIR / "prompts"
        self.LOGS_DIR = self.BASE_DIR / "logs"
        
        # Create directories if they don't exist
        self._create_directories()
        
        # Database configuration
        self.DATABASE_URL = os.getenv(
            "DATABASE_URL", f"sqlite:///{self.DB_DIR}/concepts.db"
        )
        
        # LLM configuration
        self.LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        self.OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
        self.OPENAI_MAX_TOKENS = self._parse_int(
            "OPENAI_MAX_TOKENS", 8192, min_value=1
        )
        self.OPENAI_TEMPERATURE = self._parse_float(
            "OPENAI_TEMPERATURE", 0.0, min_value=0.0, max_value=1.0
        )
        
        # Chunking configuration
        self.MAX_CHUNK_SIZE = self._parse_int("MAX_CHUNK_SIZE", 4000, min_value=100)
        self.CHUNK_OVERLAP = self._parse_int("CHUNK_OVERLAP", 200, min_value=0)
        
        # Rate limiting
        self.RATE_LIMIT_CALLS = self._parse_int("RATE_LIMIT_CALLS", 20, min_value=1)
        self.RATE_LIMIT_BATCH_SIZE = self._parse_int(
            "RATE_LIMIT_BATCH_SIZE", 5, min_value=1
        )
        
        # PDF processing
        self.OCR_ENABLED = os.getenv("OCR_ENABLED", "false").lower() == "true"
        self.TESSERACT_PATH = os.getenv("TESSERACT_PATH", "")
        
        # Logging
        self.LOG_LEVEL = self._parse_log_level(os.getenv("LOG_LEVEL", "INFO"))
        
        # Mark as initialized
        self._initialized = True
        logger.info("Configuration initialized")
    
    def _create_directories(self) -> None:
        """Create required directories if they don't exist."""
        directories = [
            self.PDF_DIR,
            self.EXTRACTED_DIR,
            self.DB_DIR,
            self.PROMPTS_DIR,
            self.LOGS_DIR,
        ]
        
        for directory in directories:
            try:
                directory.mkdir(exist_ok=True, parents=True)
            except Exception as e:
                logger.error(f"Error creating directory {directory}: {e}")
                raise
    
    def _parse_int(
        self, env_var: str, default: int, min_value: Optional[int] = None, 
        max_value: Optional[int] = None
    ) -> int:
        """
        Parse an integer from an environment variable with validation.
        
        Args:
            env_var: Environment variable name
            default: Default value if not found or invalid
            min_value: Optional minimum allowed value
            max_value: Optional maximum allowed value
            
        Returns:
            Parsed integer value
        """
        try:
            value = int(os.getenv(env_var, str(default)))
            
            # Apply constraints
            if min_value is not None and value < min_value:
                logger.warning(
                    f"{env_var} value {value} is below minimum {min_value}, "
                    f"using minimum value"
                )
                return min_value
                
            if max_value is not None and value > max_value:
                logger.warning(
                    f"{env_var} value {value} is above maximum {max_value}, "
                    f"using maximum value"
                )
                return max_value
                
            return value
        except ValueError:
            logger.warning(
                f"Invalid {env_var} value, using default: {default}"
            )
            return default
    
    def _parse_float(
        self, env_var: str, default: float, min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> float:
        """
        Parse a float from an environment variable with validation.
        
        Args:
            env_var: Environment variable name
            default: Default value if not found or invalid
            min_value: Optional minimum allowed value
            max_value: Optional maximum allowed value
            
        Returns:
            Parsed float value
        """
        try:
            value = float(os.getenv(env_var, str(default)))
            
            # Apply constraints
            if min_value is not None and value < min_value:
                logger.warning(
                    f"{env_var} value {value} is below minimum {min_value}, "
                    f"using minimum value"
                )
                return min_value
                
            if max_value is not None and value > max_value:
                logger.warning(
                    f"{env_var} value {value} is above maximum {max_value}, "
                    f"using maximum value"
                )
                return max_value
                
            return value
        except ValueError:
            logger.warning(
                f"Invalid {env_var} value, using default: {default}"
            )
            return default
    
    def _parse_log_level(self, level_str: str) -> int:
        """
        Parse logging level from string.
        
        Args:
            level_str: String representation of log level
            
        Returns:
            Logging level as an integer
        """
        levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        
        level_str = level_str.upper()
        if level_str in levels:
            return levels[level_str]
        
        logger.warning(f"Unknown log level: {level_str}, defaulting to INFO")
        return logging.INFO
    
    def as_dict(self) -> Dict[str, Any]:
        """
        Return the current configuration as a dictionary.
        
        Returns:
            Dictionary with all configuration values
        """
        return {
            "base_dir": str(self.BASE_DIR),
            "pdf_dir": str(self.PDF_DIR),
            "extracted_dir": str(self.EXTRACTED_DIR),
            "db_dir": str(self.DB_DIR),
            "prompts_dir": str(self.PROMPTS_DIR),
            "logs_dir": str(self.LOGS_DIR),
            "database_url": self.DATABASE_URL,
            "llm_provider": self.LLM_PROVIDER,
            "openai_model": self.OPENAI_MODEL,
            "openai_max_tokens": self.OPENAI_MAX_TOKENS,
            "openai_temperature": self.OPENAI_TEMPERATURE,
            "max_chunk_size": self.MAX_CHUNK_SIZE,
            "chunk_overlap": self.CHUNK_OVERLAP,
            "rate_limit_calls": self.RATE_LIMIT_CALLS,
            "rate_limit_batch_size": self.RATE_LIMIT_BATCH_SIZE,
            "ocr_enabled": self.OCR_ENABLED,
            "tesseract_path": self.TESSERACT_PATH,
            "log_level": self.LOG_LEVEL,
        }
    
    def validate(self) -> List[str]:
        """
        Validate the configuration.
        
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        # Check API key is provided if using OpenAI
        if self.LLM_PROVIDER == "openai" and not self.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is required when LLM_PROVIDER is 'openai'")
            
        # Check Tesseract path is provided if OCR is enabled
        if self.OCR_ENABLED and not self.TESSERACT_PATH:
            errors.append("TESSERACT_PATH is required when OCR_ENABLED is true")
            
        return errors


# Singleton instance
config = Config()

# For backwards compatibility
BASE_DIR = config.BASE_DIR
PDF_DIR = config.PDF_DIR
EXTRACTED_DIR = config.EXTRACTED_DIR
DB_DIR = config.DB_DIR
PROMPTS_DIR = config.PROMPTS_DIR
DATABASE_URL = config.DATABASE_URL
LLM_PROVIDER = config.LLM_PROVIDER
OPENAI_API_KEY = config.OPENAI_API_KEY
OPENAI_MODEL = config.OPENAI_MODEL
OPENAI_MAX_TOKENS = config.OPENAI_MAX_TOKENS
OPENAI_TEMPERATURE = config.OPENAI_TEMPERATURE
MAX_CHUNK_SIZE = config.MAX_CHUNK_SIZE
CHUNK_OVERLAP = config.CHUNK_OVERLAP
RATE_LIMIT_CALLS = config.RATE_LIMIT_CALLS
RATE_LIMIT_BATCH_SIZE = config.RATE_LIMIT_BATCH_SIZE
OCR_ENABLED = config.OCR_ENABLED
TESSERACT_PATH = config.TESSERACT_PATH


def get_config() -> Dict[str, Any]:
    """
    Return the current configuration as a dictionary.
    
    This function is maintained for backwards compatibility.
    
    Returns:
        Dictionary with all configuration values
    """
    return config.as_dict()
