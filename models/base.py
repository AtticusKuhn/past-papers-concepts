"""
Base models for SQLAlchemy ORM.

This module re-exports the database components from utils.db
to maintain backwards compatibility while transitioning to the new structure.
"""

# Re-export Base and database utilities from utils.db
from utils.db import Base, db_session, init_db
