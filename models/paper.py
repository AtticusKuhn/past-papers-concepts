"""
Paper model for representing exam papers.

This module defines the Paper model which stores metadata about exam papers.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from models.base import Base


class Paper(Base):
    """
    Model representing a past paper document.

    This stores metadata about the paper including year, course, paper number,
    and processing status.
    """

    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False, index=True)
    course = Column(String, nullable=False, index=True)
    paper_number = Column(Integer, nullable=False)
    filename = Column(String, nullable=False, unique=True)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    occurrences = relationship(
        "Occurrence", back_populates="paper", cascade="all, delete-orphan"
    )

    def __init__(self, year: int, course: str, paper_number: int, filename: str):
        """
        Initialize a Paper instance.

        Args:
            year: The year of the exam paper
            course: The course code or name
            paper_number: The paper number
            filename: The filename of the PDF
        """
        self.year = year
        self.course = course
        self.paper_number = paper_number
        self.filename = filename
        self.processed_at = None

    def mark_processed(self):
        """Mark the paper as processed with the current timestamp."""
        self.processed_at = datetime.utcnow()

    def __repr__(self) -> str:
        """String representation of the paper."""
        return f"<Paper(year={self.year}, course='{self.course}', number={self.paper_number})>"
