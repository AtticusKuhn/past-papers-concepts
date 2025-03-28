"""
Database utilities for the Past Paper Concept Analyzer.

This module provides helper functions for database operations,
including transaction management and connection pooling.
"""

import logging
from contextlib import contextmanager
from typing import Any, Generator, TypeVar

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

import config
from utils.logging_config import setup_logger

# Configure logger
logger = setup_logger(__name__, logging.INFO)

# Create SQLAlchemy engine using the DATABASE_URL from config
engine = create_engine(config.DATABASE_URL)

# Create a sessionmaker for creating database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
session = SessionLocal()
# Create the Base class for declarative models
Base = declarative_base()

# Type variable for session yield
T = TypeVar('T')


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """
    Provide a transactional scope around a series of operations.
    
    This context manager handles creating and closing the session,
    as well as rolling back transactions on error.
    
    Yields:
        SQLAlchemy session
    """
    
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database error: {e}")
        raise


def init_db() -> None:
    """
    Initialize the database by creating all tables.

    This should be called when the application starts.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def get_or_create(
    session: Session, model: Any, defaults: dict = None, **kwargs
) -> tuple[Any, bool]:
    """
    Get an instance of a model, or create it if it doesn't exist.
    
    Args:
        session: SQLAlchemy session
        model: SQLAlchemy model class
        defaults: Dictionary of default values for creation
        **kwargs: Filters for query
        
    Returns:
        Tuple of (instance, created) where created is a boolean
    """
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    
    # Instance doesn't exist, create it
    params = {**kwargs}
    if defaults:
        params.update(defaults)
    
    instance = model(**params)
    try:
        session.add(instance)
        session.flush()
        return instance, True
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating {model.__name__}: {e}")
        raise
