"""Unified FastAPI Application - Merges FastAPI backend with GrapheneOS flashing"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

# Import unified config
from app.config import settings

# Import secure logging
try:
    from app.core.secure_logging import setup_secure_logging
    setup_secure_logging()
    logger = logging.getLogger(__name__)
except ImportError:
    # Fallback to basic logging if secure_logging not available
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    logger = logging.getLogger(__name__)

# Import database and Redis (if available)
try:
    from app.core.database import init_db, close_db
    from app.core.redis_client import init_redis, close_redis
    HAS_DB = True
except ImportError:
    HAS_DB = False
    logger.warning("Database and Redis modules not available. Some features will be disabled.")

# Import security middleware (if available)
try:
    from app.middleware.security import RateLimitMiddleware, SecurityHeadersMiddleware
    HAS_SECURITY = True
except ImportError:
    HAS_SECURITY = False
    logger.warning("Security middleware not available. Running without rate limiting.")

# Import GrapheneOS routes
from app.routes import devices, bundles, flash, source, build, apks

# Import FastAPI API routes (if available)
try:
    from app.api.v1.router import api_router
    HAS_API_ROUTES = True
except ImportError:
    HAS_API_ROUTES = False
    logger.warning("API v1 routes not available. Only GrapheneOS routes will be available.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting unified GrapheneOS Installer API server...")
    
    if HAS_DB:
        try:
            await init_db()
            await init_redis()
            logger.info("Database and Redis initialized")
        except Exception as e:
            logger.warning(f"Database/Redis initialization failed: {e}. Continuing without DB features.")
    
    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    if HAS_DB:
        try:
            await close_redis()
            await close_db()
        except Exception:
            pass
    
    logger.info("Application shut down successfully")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-grade FastAPI backend",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Security Middleware (if available)
# Note: Rate limiting disabled for development - can be re-enabled in production if needed
if HAS_SECURITY:
    app.add_middleware(SecurityHeadersMiddleware)
    # Rate limiting disabled - uncomment if needed for production
    # app.add_middleware(
    #     RateLimitMiddleware,
    #     max_requests=100,
    #     window_seconds=3600,
    #     exclude_paths=["/health", "/docs", "/openapi.json", "/redoc"],
    # )

# CORS Middleware - Allow all origins (no restrictions)
# Note: This allows all origins for development. For production, you may want to restrict this.
logger.info("CORS: Allowing all origins (no restrictions)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins - no restrictions
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Include GrapheneOS routers (legacy routes for compatibility)
app.include_router(devices.router, prefix="/devices", tags=["devices"])
app.include_router(bundles.router, prefix="/bundles", tags=["bundles"])
app.include_router(flash.router, prefix="/flash", tags=["flash"])
app.include_router(source.router, prefix="/source", tags=["source"])
app.include_router(build.router, prefix="/build", tags=["build"])
app.include_router(apks.router, prefix="/apks", tags=["apks"])

# Include FastAPI v1 API routes (if available)
if HAS_API_ROUTES:
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "GrapheneOS Installer API",
        "version": settings.APP_VERSION,
        "status": "healthy",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "service": "GrapheneOS Installer API",
    }


@app.get("/tools/check")
async def check_tools():
    """Check if ADB and Fastboot are available"""
    from app.utils.tools import check_tool_availability
    
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


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc) if settings.DEBUG else "An error occurred",
        },
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.PY_HOST,
        port=settings.PY_PORT,
        reload=settings.DEBUG,
        log_config=None,  # Use our custom logging
    )

