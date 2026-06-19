# Import every model here so that:
# 1. SQLAlchemy's mapper registry is fully populated before any query runs.
# 2. Alembic's env.py (target_metadata = Base.metadata) picks up all tables
#    during `alembic revision --autogenerate`.

from app.models.link import ExtractionStatus, SavedLink
from app.models.note import Note
from app.models.project import Project
from app.models.tag import LinkTag, NoteTag, Tag
from app.models.user import User

__all__ = [
    "User",
    "Project",
    "Note",
    "SavedLink",
    "ExtractionStatus",
    "Tag",
    "NoteTag",
    "LinkTag",
]
