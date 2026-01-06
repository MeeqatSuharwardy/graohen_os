from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn
import logging
from .config import settings
from .routes import devices, bundles, flash, source, build

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger(__name__)
logger.info("Starting FlashDash API server")

app = FastAPI(
    title="FlashDash API",
    description="GrapheneOS Flashing Dashboard Backend",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(devices.router, prefix="/devices", tags=["devices"])
app.include_router(bundles.router, prefix="/bundles", tags=["bundles"])
app.include_router(flash.router, prefix="/flash", tags=["flash"])
app.include_router(source.router, prefix="/source", tags=["source"])
app.include_router(build.router, prefix="/build", tags=["build"])


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "FlashDash API"}


@app.get("/tools/check")
async def check_tools():
    """Check if ADB and Fastboot are available"""
    from .utils.tools import check_tool_availability
    
    adb_ok = check_tool_availability(settings.ADB_PATH)
    fastboot_ok = check_tool_availability(settings.FASTBOOT_PATH)
    
    return {
        "adb": {
            "available": adb_ok,
            "path": settings.ADB_PATH,
        },
        "fastboot": {
            "available": fastboot_ok,
            "path": settings.FASTBOOT_PATH,
        },
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.PY_HOST,
        port=settings.PY_PORT,
        reload=True,
    )

