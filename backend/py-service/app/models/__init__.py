"""Database Models"""

from app.core.database import Base
from app.models.user import User

# Import all models here for Alembic to detect them
__all__ = ["Base", "User"]

