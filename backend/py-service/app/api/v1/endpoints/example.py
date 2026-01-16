"""Example API Endpoint"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.logging import setup_logging

logger = setup_logging().getLogger(__name__)

router = APIRouter()


@router.get("/example")
async def get_example(db: AsyncSession = Depends(get_db)):
    """
    Example endpoint
    Demonstrates basic structure for API endpoints
    """
    try:
        # Your business logic here
        logger.info("Example endpoint called")
        
        return {
            "message": "This is an example endpoint",
            "database_connected": db is not None,
        }
    except Exception as e:
        logger.error(f"Error in example endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred",
        )

