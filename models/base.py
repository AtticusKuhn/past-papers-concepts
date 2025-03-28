"""
Base models for SQLAlchemy ORM.

This module defines the Base class and engine connection for all models.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import config

# Create SQLAlchemy engine using the DATABASE_URL from config
engine = create_engine(config.DATABASE_URL)

# Create a sessionmaker for creating database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the Base class for declarative models
Base = declarative_base()


def get_db():
    """
    Get a database session.

    Usage:
        with get_db() as db:
            db.query(Model).all()

    Returns:
        SQLAlchemy session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize the database by creating all tables.

    This should be called when the application starts.
    """
    Base.metadata.create_all(bind=engine)
