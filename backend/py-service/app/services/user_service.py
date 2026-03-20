"""PostgreSQL user service - auth"""

from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import database
from app.models.user import User
from app.core.security import hash_password
import logging

logger = logging.getLogger(__name__)


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email from PostgreSQL."""
    if database.AsyncSessionLocal is None:
        return None
    async with database.AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()
        if not user:
            return None
        return {
            "id": str(user.id),
            "email": user.email,
            "hashed_password": user.hashed_password,
            "full_name": user.full_name,
            "is_active": user.is_active,
        }


async def create_user(email: str, password: str, full_name: Optional[str] = None) -> Dict[str, Any]:
    """Create user in PostgreSQL. Raises ValueError if email exists."""
    if database.AsyncSessionLocal is None:
        raise RuntimeError("Database not initialized")
    async with database.AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email.lower()))
        if result.scalar_one_or_none():
            raise ValueError("Email already registered")
        user = User(
            email=email.lower(),
            hashed_password=hash_password(password),
            full_name=full_name,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return {
            "id": str(user.id),
            "email": user.email,
            "hashed_password": user.hashed_password,
            "full_name": user.full_name,
            "is_active": user.is_active,
        }


class UserService:
    """PostgreSQL user service."""

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        return await get_user_by_email(email)

    async def create_user(self, email: str, password: str, full_name: Optional[str] = None) -> Dict[str, Any]:
        return await create_user(email, password, full_name)


_user_service: Optional[UserService] = None


def get_user_service() -> UserService:
    """Return user service instance."""
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service
