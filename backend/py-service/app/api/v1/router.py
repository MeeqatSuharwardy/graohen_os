"""API v1 Router"""

from fastapi import APIRouter

# Import route modules here
from app.api.v1.endpoints import example, auth, email, drive, public
from app.api.v1.endpoints.grapheneos import download

api_router = APIRouter()

# Include routers
api_router.include_router(example.router, prefix="/example", tags=["example"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(email.router, prefix="/email", tags=["email"])
api_router.include_router(drive.router, prefix="/drive", tags=["drive"])
api_router.include_router(public.router, prefix="/public", tags=["public"])
api_router.include_router(download.router, tags=["grapheneos"])

# Example for more endpoints:
# from app.api.v1.endpoints import users
# api_router.include_router(users.router, prefix="/users", tags=["users"])


@api_router.get("/")
async def api_root():
    """API root endpoint"""
    return {
        "message": "API v1",
        "status": "active",
        "version": "1.0.0",
    }

