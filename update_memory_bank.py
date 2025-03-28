#!/usr/bin/env python
"""
Memory Bank updater for Past Paper Concept Analyzer.

This script updates the activeContext.md and progress.md files in the memory-bank
directory to reflect the current state of the project.
"""

import json
import os
from datetime import datetime
from pathlib import Path

from sqlalchemy import distinct, func

from models.base import get_db, init_db
from models.concept import Concept, ConceptRelation, Occurrence
from models.paper import Paper


def get_project_stats():
    """Get current statistics about the project."""
    init_db()
    with next(get_db()) as db:
        # Get paper counts
        total_papers = db.query(func.count(Paper.id)).scalar() or 0
        processed_papers = (
            db.query(func.count(Paper.id))
            .filter(Paper.processed_at.isnot(None))
            .scalar()
            or 0
        )

        # Get concept counts
        total_concepts = db.query(func.count(Concept.id)).scalar() or 0
        categories = db.query(func.count(distinct(Concept.category))).scalar() or 0

        # Get relation counts
        total_relations = db.query(func.count(ConceptRelation.id)).scalar() or 0

        # Get occurrence counts
        total_occurrences = db.query(func.count(Occurrence.id)).scalar() or 0

        # Get years covered
        years = db.query(func.min(Paper.year), func.max(Paper.year)).first() or (
            None,
            None,
        )
        min_year, max_year = years

        # Get most common concepts
        top_concepts = (
            db.query(Concept.name, func.count(Occurrence.id).label("count"))
            .join(Occurrence)
            .group_by(Concept.id)
            .order_by(func.count(Occurrence.id).desc())
            .limit(5)
            .all()
        )

        # Get most common categories
        top_categories = (
            db.query(Concept.category, func.count(Concept.id).label("count"))
            .filter(Concept.category.isnot(None))
            .group_by(Concept.category)
            .order_by(func.count(Concept.id).desc())
            .limit(5)
            .all()
        )

    return {
        "papers": {"total": total_papers, "processed": processed_papers},
        "concepts": {
            "total": total_concepts,
            "categories": categories,
            "top": [{"name": name, "count": count} for name, count in top_concepts],
            "top_categories": [
                {"name": cat, "count": count} for cat, count in top_categories if cat
            ],
        },
        "relations": total_relations,
        "occurrences": total_occurrences,
        "years": {"min": min_year, "max": max_year},
        "timestamp": datetime.now().isoformat(),
    }


def update_active_context(stats):
    """Update the activeContext.md file with current focus and stats."""
    memory_bank_dir = Path("memory-bank")
    active_context_path = memory_bank_dir / "activeContext.md"

    if not active_context_path.exists():
        print(f"Error: {active_context_path} not found.")
        return False

    # Read the current file
    with open(active_context_path, "r") as file:
        lines = file.readlines()

    # Update the content
    new_content = []
    in_current_focus = False
    in_next_steps = False

    for line in lines:
        # Keep existing sections but update their content
        if "## Current Focus" in line:
            in_current_focus = True
            new_content.append(line)
            new_content.append("\n")
            new_content.append(
                "The project is currently in active development. Core components are implemented and ready for testing with real data.\n\n"
            )
            new_content.append(
                f"As of {datetime.now().strftime('%Y-%m-%d')}, the system contains:\n"
            )
            new_content.append(
                f"- {stats['papers']['total']} papers ({stats['papers']['processed']} processed)\n"
            )
            new_content.append(f"- {stats['concepts']['total']} unique concepts\n")
            new_content.append(f"- {stats['occurrences']} concept occurrences\n")
            new_content.append(
                f"- {stats['relations']} relationships between concepts\n"
            )

            if stats["concepts"]["top"]:
                new_content.append("\nMost common concepts:\n")
                for concept in stats["concepts"]["top"]:
                    new_content.append(
                        f"- {concept['name']} ({concept['count']} occurrences)\n"
                    )

            continue

        if "## Recent Decisions" in line:
            in_current_focus = False
            new_content.append(line)
            continue

        if "## Next Steps" in line:
            in_next_steps = True
            new_content.append(line)
            new_content.append("\n")
            new_content.append("1. Test the system with real Cambridge Tripos papers\n")
            new_content.append("2. Refine LLM prompts for better concept extraction\n")
            new_content.append(
                "3. Enhance the query capabilities for more advanced analysis\n"
            )
            new_content.append(
                "4. Add visualizations for concept relationships and trends\n"
            )
            new_content.append(
                "5. Implement additional pre-processing for better text extraction\n"
            )
            continue

        if "## Open Questions" in line:
            in_next_steps = False
            new_content.append(line)
            continue

        if line.startswith("## "):
            in_current_focus = False
            in_next_steps = False
            new_content.append(line)
            continue

        # Skip content in sections we're replacing
        if in_current_focus or in_next_steps:
            continue

        # Keep content in other sections
        new_content.append(line)

    # Write updated content
    with open(active_context_path, "w") as file:
        file.writelines(new_content)

    print(f"Updated {active_context_path}")
    return True


def update_progress(stats):
    """Update the progress.md file with current status."""
    memory_bank_dir = Path("memory-bank")
    progress_path = memory_bank_dir / "progress.md"

    if not progress_path.exists():
        print(f"Error: {progress_path} not found.")
        return False

    # Read the current file
    with open(progress_path, "r") as file:
        lines = file.readlines()

    # Update the content
    new_content = []
    in_current_status = False
    in_completed_work = False
    in_in_progress = False
    in_upcoming_work = False
    in_milestone = False

    for line in lines:
        # Keep existing sections but update their content
        if "## Current Status" in line:
            in_current_status = True
            new_content.append(line)
            new_content.append("\n")

            if stats["papers"]["total"] == 0:
                new_content.append("**Phase**: Ready for Data\n\n")
                new_content.append(
                    "The system architecture and core components have been implemented. The project is now ready for actual paper data to be loaded and processed.\n"
                )
            else:
                new_content.append("**Phase**: Active Processing\n\n")
                new_content.append(
                    f"The system is actively processing papers. Currently, {stats['papers']['processed']} out of {stats['papers']['total']} papers have been processed, yielding {stats['concepts']['total']} unique concepts.\n"
                )

            continue

        if "## Completed Work" in line:
            in_current_status = False
            in_completed_work = True
            new_content.append(line)
            new_content.append("\n")
            new_content.append("- [x] Defined project goals and success criteria\n")
            new_content.append("- [x] Established core architectural approach\n")
            new_content.append(
                "- [x] Selected primary technologies for each component\n"
            )
            new_content.append("- [x] Determined data flow through the system\n")
            new_content.append("- [x] Identified potential technical challenges\n")
            new_content.append("- [x] Set up basic project structure\n")
            new_content.append("- [x] Implemented PDF ingestion pipeline\n")
            new_content.append("- [x] Implemented text extraction module\n")
            new_content.append("- [x] Implemented database models\n")
            new_content.append("- [x] Created concept extraction prompts\n")
            new_content.append("- [x] Implemented concept storage\n")
            new_content.append("- [x] Built query engine\n")
            continue

        if "## In Progress" in line:
            in_completed_work = False
            in_in_progress = True
            new_content.append(line)
            new_content.append("\n")
            new_content.append("- [ ] Testing with real Cambridge Tripos papers\n")
            new_content.append("- [ ] Refining LLM prompts for better extraction\n")
            new_content.append(
                "- [ ] Enhancing pre-processing for better text quality\n"
            )
            continue

        if "## Upcoming Work" in line:
            in_in_progress = False
            in_upcoming_work = True
            new_content.append(line)
            new_content.append("\n")
            new_content.append("- [ ] Add visualization capabilities\n")
            new_content.append("- [ ] Implement advanced querying features\n")
            new_content.append("- [ ] Create user-friendly interface\n")
            new_content.append("- [ ] Add support for exporting analysis results\n")
            new_content.append("- [ ] Implement trend analysis over multiple years\n")
            continue

        if "## Known Issues & Challenges" in line:
            in_upcoming_work = False
            new_content.append(line)
            continue

        if "## Next Milestone" in line:
            in_milestone = True
            new_content.append(line)
            new_content.append("\n")
            new_content.append(
                "Processing a batch of real Cambridge Computer Science Tripos papers and extracting meaningful concepts that demonstrate the system's capabilities.\n"
            )
            continue

        if line.startswith("## "):
            in_current_status = False
            in_completed_work = False
            in_in_progress = False
            in_upcoming_work = False
            in_milestone = False
            new_content.append(line)
            continue

        # Skip content in sections we're replacing
        if (
            in_current_status
            or in_completed_work
            or in_in_progress
            or in_upcoming_work
            or in_milestone
        ):
            continue

        # Keep content in other sections
        new_content.append(line)

    # Write updated content
    with open(progress_path, "w") as file:
        file.writelines(new_content)

    print(f"Updated {progress_path}")
    return True


def save_stats_json(stats):
    """Save stats to a JSON file for later reference."""
    stats_path = Path("db") / "stats.json"
    os.makedirs(stats_path.parent, exist_ok=True)

    with open(stats_path, "w") as file:
        json.dump(stats, file, indent=2)

    print(f"Saved stats to {stats_path}")
    return True


def main():
    """Main function to update Memory Bank files."""
    print("Gathering project statistics...")
    stats = get_project_stats()

    print("Updating Memory Bank files...")
    update_active_context(stats)
    update_progress(stats)
    save_stats_json(stats)

    print("Memory Bank update complete!")


if __name__ == "__main__":
    main()
