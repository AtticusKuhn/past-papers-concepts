"""
Query Engine for the Past Paper Concept Analyzer.

This module provides functionality to query and analyze concepts extracted from papers.
It supports various types of queries to explore the concept database.
"""

import logging
from collections import defaultdict
from typing import Any, Dict, List

from sqlalchemy import and_, desc, distinct, func, or_
from sqlalchemy.orm import joinedload

from models.base import get_db, init_db
from models.concept import Concept, ConceptRelation, Occurrence
from models.paper import Paper

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class QueryEngine:
    """
    Engine for querying and analyzing concepts in the database.

    This class provides methods to:
    1. Get concept frequencies
    2. Get concepts by category
    3. Get concepts for specific papers or years
    4. Find related concepts
    5. Search concepts by keyword
    6. Analyze trends over time
    """

    def __init__(self):
        """Initialize the QueryEngine."""
        pass

    def get_concept_frequency(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Get concepts ordered by frequency (number of occurrences).

        Args:
            limit: Optional maximum number of concepts to return

        Returns:
            List of dictionaries with concept information and occurrence count
        """
        with next(get_db()) as db:
            # Query for concepts with their occurrence count
            query = (
                db.query(Concept, func.count(Occurrence.id).label("occurrence_count"))
                .join(Occurrence)
                .group_by(Concept.id)
                .order_by(desc("occurrence_count"))
            )

            if limit:
                query = query.limit(limit)

            results = query.all()

            # Format results
            return [
                {
                    "id": concept.id,
                    "name": concept.name,
                    "category": concept.category,
                    "description": concept.description,
                    "occurrence_count": count,
                }
                for concept, count in results
            ]

    def get_concepts_by_category(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get concepts grouped by category.

        Returns:
            Dictionary mapping categories to lists of concepts
        """
        with next(get_db()) as db:
            # Get all concepts with a category
            concepts = db.query(Concept).filter(Concept.category.isnot(None)).all()

            # Group by category
            categories = defaultdict(list)
            for concept in concepts:
                category = concept.category or "Uncategorized"
                categories[category].append(
                    {
                        "id": concept.id,
                        "name": concept.name,
                        "description": concept.description,
                    }
                )

            return dict(categories)

    def get_concepts_by_year(self, year: int) -> List[Dict[str, Any]]:
        """
        Get concepts that appear in papers from a specific year.

        Args:
            year: The year to query for

        Returns:
            List of dictionaries with concept information and occurrence count
        """
        with next(get_db()) as db:
            # Query for concepts that appear in papers from the given year
            query = (
                db.query(Concept, func.count(Occurrence.id).label("occurrence_count"))
                .join(Occurrence)
                .join(Paper)
                .filter(Paper.year == year)
                .group_by(Concept.id)
                .order_by(desc("occurrence_count"))
            )

            results = query.all()

            # Format results
            return [
                {
                    "id": concept.id,
                    "name": concept.name,
                    "category": concept.category,
                    "description": concept.description,
                    "occurrence_count": count,
                }
                for concept, count in results
            ]

    def get_concepts_by_paper(self, paper_id: int) -> List[Dict[str, Any]]:
        """
        Get concepts that appear in a specific paper.

        Args:
            paper_id: ID of the paper to query for

        Returns:
            List of dictionaries with concept information and context
        """
        with next(get_db()) as db:
            # Query for occurrences in the given paper
            occurrences = (
                db.query(Occurrence)
                .filter(Occurrence.paper_id == paper_id)
                .options(joinedload(Occurrence.concept))
                .all()
            )

            # Format results
            return [
                {
                    "id": occ.concept.id,
                    "name": occ.concept.name,
                    "category": occ.concept.category,
                    "description": occ.concept.description,
                    "context": occ.context,
                    "confidence": occ.confidence,
                    "question": occ.question,
                }
                for occ in occurrences
            ]

    def get_related_concepts(self, concept_id: int) -> List[Dict[str, Any]]:
        """
        Get concepts related to a specific concept.

        Args:
            concept_id: ID of the concept to find relations for

        Returns:
            List of dictionaries with related concept information
        """
        with next(get_db()) as db:
            # Get the concept
            concept = db.query(Concept).filter(Concept.id == concept_id).first()
            if not concept:
                return []

            # Get related concepts (both directions)
            related_to = (
                db.query(
                    Concept, ConceptRelation.relation_type, ConceptRelation.strength
                )
                .join(ConceptRelation, ConceptRelation.concept2_id == Concept.id)
                .filter(ConceptRelation.concept1_id == concept_id)
                .all()
            )

            related_from = (
                db.query(
                    Concept, ConceptRelation.relation_type, ConceptRelation.strength
                )
                .join(ConceptRelation, ConceptRelation.concept1_id == Concept.id)
                .filter(ConceptRelation.concept2_id == concept_id)
                .all()
            )

            # Format results
            result = []

            for related, relation_type, strength in related_to:
                result.append(
                    {
                        "id": related.id,
                        "name": related.name,
                        "category": related.category,
                        "description": related.description,
                        "relation_type": relation_type,
                        "direction": "to",
                        "strength": strength,
                    }
                )

            for related, relation_type, strength in related_from:
                result.append(
                    {
                        "id": related.id,
                        "name": related.name,
                        "category": related.category,
                        "description": related.description,
                        "relation_type": relation_type,
                        "direction": "from",
                        "strength": strength,
                    }
                )

            return result

    def search_concepts(self, query: str) -> List[Dict[str, Any]]:
        """
        Search concepts by keyword.

        Args:
            query: Search query string

        Returns:
            List of dictionaries with matching concept information
        """
        with next(get_db()) as db:
            # Search in name, category, and description
            search_pattern = f"%{query}%"
            concepts = (
                db.query(Concept)
                .filter(
                    or_(
                        Concept.name.ilike(search_pattern),
                        Concept.category.ilike(search_pattern),
                        Concept.description.ilike(search_pattern),
                    )
                )
                .all()
            )

            # Format results
            return [
                {
                    "id": concept.id,
                    "name": concept.name,
                    "category": concept.category,
                    "description": concept.description,
                }
                for concept in concepts
            ]

    def get_yearly_trends(
        self, concept_ids: List[int] = None, top_n: int = 20
    ) -> Dict[str, Any]:
        """
        Get trends of concept occurrences over years.

        Args:
            concept_ids: Optional list of concept IDs to filter for
            top_n: If concept_ids is not provided, use the top N most frequent concepts

        Returns:
            Dictionary with trend data
        """
        with next(get_db()) as db:
            # Get list of all years in the database
            years = [
                year[0]
                for year in db.query(distinct(Paper.year)).order_by(Paper.year).all()
            ]

            # If no concept IDs provided, get the top N concepts
            if not concept_ids:
                # Get top N concepts by frequency
                top_concepts_query = (
                    db.query(Concept.id, func.count(Occurrence.id).label("count"))
                    .join(Occurrence)
                    .group_by(Concept.id)
                    .order_by(desc("count"))
                    .limit(top_n)
                )

                concept_ids = [c_id for c_id, _ in top_concepts_query.all()]

            # Get all the concepts we need
            concepts = db.query(Concept).filter(Concept.id.in_(concept_ids)).all()
            concept_map = {c.id: c for c in concepts}

            # Initialize trend data
            trend_data = {"years": years, "concepts": [], "data": {}}

            # For each concept, get yearly occurrence counts
            for concept_id in concept_ids:
                concept = concept_map.get(concept_id)
                if not concept:
                    continue

                trend_data["concepts"].append(
                    {
                        "id": concept.id,
                        "name": concept.name,
                        "category": concept.category,
                    }
                )

                # Get occurrence count for each year
                year_counts = {}
                for year in years:
                    count = (
                        db.query(func.count(Occurrence.id))
                        .join(Paper)
                        .filter(
                            and_(
                                Occurrence.concept_id == concept_id, Paper.year == year
                            )
                        )
                        .scalar()
                    )

                    year_counts[str(year)] = count

                trend_data["data"][concept.name] = year_counts

            return trend_data

    def get_concept_co_occurrence(
        self, concept_id: int, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get concepts that frequently co-occur with a given concept.

        Args:
            concept_id: ID of the concept to find co-occurrences for
            limit: Maximum number of co-occurring concepts to return

        Returns:
            List of dictionaries with co-occurring concept information
        """
        with next(get_db()) as db:
            # Get papers where the concept occurs
            paper_ids = [
                p_id
                for p_id, in db.query(Occurrence.paper_id)
                .filter(Occurrence.concept_id == concept_id)
                .distinct()
            ]

            if not paper_ids:
                return []

            # Get other concepts that occur in the same papers
            co_concepts = (
                db.query(
                    Concept,
                    func.count(distinct(Occurrence.paper_id)).label("paper_count"),
                )
                .join(Occurrence)
                .filter(
                    and_(
                        Occurrence.paper_id.in_(paper_ids),
                        Occurrence.concept_id != concept_id,
                    )
                )
                .group_by(Concept.id)
                .order_by(desc("paper_count"))
                .limit(limit)
                .all()
            )

            # Format results
            return [
                {
                    "id": concept.id,
                    "name": concept.name,
                    "category": concept.category,
                    "description": concept.description,
                    "co_occurrence_count": count,
                }
                for concept, count in co_concepts
            ]

    def get_papers(self, year: int = None, course: str = None) -> List[Dict[str, Any]]:
        """
        Get papers with optional filtering by year or course.

        Args:
            year: Optional year filter
            course: Optional course filter

        Returns:
            List of dictionaries with paper information
        """
        with next(get_db()) as db:
            query = db.query(Paper)

            if year:
                query = query.filter(Paper.year == year)

            if course:
                query = query.filter(Paper.course == course)

            papers = query.order_by(
                Paper.year.desc(), Paper.course, Paper.paper_number
            ).all()

            # Format results
            return [
                {
                    "id": paper.id,
                    "year": paper.year,
                    "course": paper.course,
                    "paper_number": paper.paper_number,
                    "filename": paper.filename,
                    "processed_at": (
                        paper.processed_at.isoformat() if paper.processed_at else None
                    ),
                }
                for paper in papers
            ]

    def get_concept_details(self, concept_id: int) -> Dict[str, Any]:
        """
        Get detailed information about a concept.

        Args:
            concept_id: ID of the concept

        Returns:
            Dictionary with concept details
        """
        with next(get_db()) as db:
            # Get the concept
            concept = db.query(Concept).filter(Concept.id == concept_id).first()
            if not concept:
                return {}

            # Get occurrence count
            occurrence_count = (
                db.query(func.count(Occurrence.id))
                .filter(Occurrence.concept_id == concept_id)
                .scalar()
            )

            # Get paper count
            paper_count = (
                db.query(func.count(distinct(Occurrence.paper_id)))
                .filter(Occurrence.concept_id == concept_id)
                .scalar()
            )

            # Get year range
            years = (
                db.query(func.min(Paper.year), func.max(Paper.year))
                .join(Occurrence)
                .filter(Occurrence.concept_id == concept_id)
                .first()
            )

            min_year, max_year = years if years else (None, None)

            # Get parent concept
            parent = None
            if concept.parent_concept_id:
                parent_concept = (
                    db.query(Concept)
                    .filter(Concept.id == concept.parent_concept_id)
                    .first()
                )
                if parent_concept:
                    parent = {"id": parent_concept.id, "name": parent_concept.name}

            # Format results
            return {
                "id": concept.id,
                "name": concept.name,
                "category": concept.category,
                "description": concept.description,
                "parent_concept": parent,
                "occurrence_count": occurrence_count,
                "paper_count": paper_count,
                "first_year": min_year,
                "last_year": max_year,
            }


def print_table(headers: List[str], rows: List[List[Any]]):
    """
    Print data as a formatted ASCII table.

    Args:
        headers: List of column headers
        rows: List of rows, each row being a list of values
    """
    # Determine column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            val_str = str(val)
            widths[i] = max(widths[i], len(val_str))

    # Print headers
    header_row = " | ".join(h.ljust(w) for h, w in zip(headers, widths))
    print(header_row)
    print("-" * len(header_row))

    # Print data rows
    for row in rows:
        row_str = " | ".join(str(val).ljust(w) for val, w in zip(row, widths))
        print(row_str)


def main():
    """Run the query engine as a standalone script."""
    # Initialize database
    init_db()

    # Create query engine
    query_engine = QueryEngine()

    # Get top concepts by frequency
    print("\n=== TOP 10 CONCEPTS BY FREQUENCY ===")
    top_concepts = query_engine.get_concept_frequency(limit=10)

    if top_concepts:
        print_table(
            ["ID", "Name", "Category", "Occurrences"],
            [
                [c["id"], c["name"], c["category"] or "N/A", c["occurrence_count"]]
                for c in top_concepts
            ],
        )
    else:
        print("No concepts found in the database.")

    # Get concepts by category
    print("\n=== CONCEPTS BY CATEGORY ===")
    categories = query_engine.get_concepts_by_category()

    for category, concepts in categories.items():
        print(f"\n{category} ({len(concepts)} concepts):")
        for concept in concepts[:5]:  # Show only top 5 per category
            print(f"  - {concept['name']}")
        if len(concepts) > 5:
            print(f"  ... and {len(concepts) - 5} more")

    # Get papers
    print("\n=== RECENT PAPERS ===")
    papers = query_engine.get_papers()

    if papers:
        # Show only 5 most recent papers
        print_table(
            ["ID", "Year", "Course", "Paper"],
            [[p["id"], p["year"], p["course"], p["paper_number"]] for p in papers[:5]],
        )
    else:
        print("No papers found in the database.")


if __name__ == "__main__":
    main()
