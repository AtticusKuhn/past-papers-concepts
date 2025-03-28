"""
Concept models for representing extracted concepts and their relationships.

This module defines the Concept, ConceptRelation, and Occurrence models
which form the core of the concept database.
"""

from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from models.base import Base


class Concept(Base):
    """
    Model representing a computer science concept extracted from papers.

    This stores the concept name, category, description, and optional parent concept.
    """

    __tablename__ = "concepts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True, unique=True)
    category = Column(String, nullable=True, index=True)
    description = Column(Text, nullable=True)
    parent_concept_id = Column(Integer, ForeignKey("concepts.id"), nullable=True)

    # Self-referential relationship for hierarchical concepts
    parent_concept = relationship("Concept", remote_side=[id], backref="child_concepts")

    # Relationships
    occurrences = relationship(
        "Occurrence", back_populates="concept", cascade="all, delete-orphan"
    )
    related_from = relationship(
        "ConceptRelation",
        foreign_keys="ConceptRelation.concept1_id",
        back_populates="concept1",
    )
    related_to = relationship(
        "ConceptRelation",
        foreign_keys="ConceptRelation.concept2_id",
        back_populates="concept2",
    )

    def __init__(
        self,
        name: str,
        category: str = None,
        description: str = None,
        parent_concept_id: int = None,
    ):
        """
        Initialize a Concept instance.

        Args:
            name: The concept name
            category: Optional category (e.g., "Algorithms", "Networking")
            description: Optional description of the concept
            parent_concept_id: Optional ID of a parent concept
        """
        self.name = name
        self.category = category
        self.description = description
        self.parent_concept_id = parent_concept_id

    def __repr__(self) -> str:
        """String representation of the concept."""
        return f"<Concept(name='{self.name}', category='{self.category}')>"


class ConceptRelation(Base):
    """
    Model representing a relationship between two concepts.

    This captures how concepts are related to each other, with a relation type and strength.
    """

    __tablename__ = "concept_relations"

    id = Column(Integer, primary_key=True, index=True)
    concept1_id = Column(Integer, ForeignKey("concepts.id"), nullable=False)
    concept2_id = Column(Integer, ForeignKey("concepts.id"), nullable=False)
    relation_type = Column(
        String, nullable=False
    )  # e.g., "prerequisite", "related", "includes"
    strength = Column(Float, nullable=False, default=1.0)  # 0.0 to 1.0

    # Relationships
    concept1 = relationship(
        "Concept", foreign_keys=[concept1_id], back_populates="related_from"
    )
    concept2 = relationship(
        "Concept", foreign_keys=[concept2_id], back_populates="related_to"
    )

    def __init__(
        self,
        concept1_id: int,
        concept2_id: int,
        relation_type: str,
        strength: float = 1.0,
    ):
        """
        Initialize a ConceptRelation instance.

        Args:
            concept1_id: ID of the first concept
            concept2_id: ID of the second concept
            relation_type: Type of relationship
            strength: Strength of relationship (0.0 to 1.0)
        """
        self.concept1_id = concept1_id
        self.concept2_id = concept2_id
        self.relation_type = relation_type
        self.strength = min(max(strength, 0.0), 1.0)  # Ensure between 0 and 1

    def __repr__(self) -> str:
        """String representation of the concept relation."""
        return f"<ConceptRelation({self.concept1_id} -{self.relation_type}-> {self.concept2_id})>"


class Occurrence(Base):
    """
    Model representing an occurrence of a concept in a specific paper.

    This links concepts to papers with additional context like question number and confidence.
    """

    __tablename__ = "occurrences"

    id = Column(Integer, primary_key=True, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.id"), nullable=False)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False)
    question = Column(String, nullable=True)  # Question number or identifier
    context = Column(Text, nullable=True)  # Surrounding text for context
    confidence = Column(Float, nullable=False, default=1.0)  # 0.0 to 1.0

    # Relationships
    concept = relationship("Concept", back_populates="occurrences")
    paper = relationship("Paper", back_populates="occurrences")

    def __init__(
        self,
        concept_id: int,
        paper_id: int,
        question: str = None,
        context: str = None,
        confidence: float = 1.0,
    ):
        """
        Initialize an Occurrence instance.

        Args:
            concept_id: ID of the concept
            paper_id: ID of the paper
            question: Optional question number or identifier
            context: Optional surrounding text for context
            confidence: Confidence score (0.0 to 1.0)
        """
        self.concept_id = concept_id
        self.paper_id = paper_id
        self.question = question
        self.context = context
        self.confidence = min(max(confidence, 0.0), 1.0)  # Ensure between 0 and 1

    def __repr__(self) -> str:
        """String representation of the occurrence."""
        return f"<Occurrence(concept_id={self.concept_id}, paper_id={self.paper_id})>"
