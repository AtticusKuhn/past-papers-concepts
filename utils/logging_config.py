"""
Centralized logging configuration for the Past Paper Concept Analyzer.

This module configures logging for the entire application, ensuring consistent
logging behavior across all components.
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Union


def setup_logger(
    name: str,
    level: Union[int, str] = logging.INFO,
    log_file: Optional[Union[str, Path]] = None,
    log_format: Optional[str] = None,
) -> logging.Logger:
    """
    Set up and configure a logger.

    Args:
        name: Logger name
        level: Logging level (default: INFO)
        log_file: Optional path to log file
        log_format: Optional custom log format

    Returns:
        Configured logger
    """
    # Set default format if not provided
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Get or create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers to prevent duplicate logs
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create handlers
    handlers = []

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    handlers.append(console_handler)

    # Add file handler if specified
    if log_file:
        # Ensure parent directory exists
        if isinstance(log_file, str):
            log_file = Path(log_file)
        log_file.parent.mkdir(exist_ok=True, parents=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(file_handler)

    # Add handlers to logger
    for handler in handlers:
        logger.addHandler(handler)

    return logger


def configure_application_logging(
    log_level: Union[int, str] = logging.INFO,
    log_files: Optional[Dict[str, Union[str, Path]]] = None,
) -> None:
    """
    Configure logging for the entire application.

    Args:
        log_level: Base logging level (default: INFO)
        log_files: Optional dictionary mapping module names to log file paths
    """
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Configure module-specific loggers if log_files is provided
    if log_files:
        for module_name, log_file in log_files.items():
            setup_logger(module_name, log_level, log_file)
