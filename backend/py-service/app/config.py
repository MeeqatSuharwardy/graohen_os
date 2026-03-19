"""Unified Application Configuration - Merges FastAPI and GrapheneOS settings"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import List

# .env path: backend/py-service/.env (relative to this file)
_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    """Unified application settings for FastAPI backend with GrapheneOS flashing support"""
    
    model_config = SettingsConfigDict(
        env_file=str(_ENV_PATH),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    
    # Application
    APP_NAME: str = "GrapheneOS Installer API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    # Server
    PY_HOST: str = "0.0.0.0"
    PY_PORT: int = 8000
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_HOSTS: str = "localhost,127.0.0.1,freedomos.vulcantech.co,vulcantech.tech"
    
    # Database - loaded from .env (DATABASE_URL)
    DATABASE_URL: str = Field(default="", description="PostgreSQL URL")
    DATABASE_CA_CERT: str = Field(
        default="ca-certificate.crt",
        description="Path to CA certificate for SSL (relative to project root or absolute)",
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_ECHO: bool = False
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: str = ""
    REDIS_MAX_CONNECTIONS: int = 10
    
    # Security
    SECRET_KEY: str = Field(
        default="change-this-secret-key-in-production-use-long-random-string",
        description="Secret key for JWT tokens",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS - Allow all origins (frontend can run on IP or any domain)
    CORS_ORIGINS: str = "*"
    
    # Storage (Drive)
    DEFAULT_STORAGE_QUOTA_BYTES: int = Field(
        default=5 * 1024 * 1024 * 1024,  # 5GB free tier
        description="Default storage quota per user in bytes",
    )
    ADMIN_EMAILS: str = Field(
        default="",
        description="Comma-separated admin emails for CMS/admin APIs",
    )

    # Email (for encrypted email service)
    EMAIL_DOMAIN: str = Field(
        default="vulcantech.tech",
        description="Email domain for generating email addresses (e.g., howie@vulcantech.tech)",
    )
    EXTERNAL_HTTPS_BASE_URL: str = Field(
        default="https://fxmail.ai",
        description="Base URL for external email links",
    )
    EMAIL_DOMAIN: str = Field(
        default="fxmail.ai",
        description="Email domain for generating email addresses",
    )
    
    # MongoDB
    MONGODB_CONNECTION_STRING: str = Field(
        default="mongodb+srv://doadmin:R6j8Oe2r1h749U5C@db-mongodb-nyc3-19012-1834d74a.mongo.ondigitalocean.com/admin?tls=true&authSource=admin",
        description="MongoDB connection string",
    )
    MONGODB_DATABASE: str = Field(
        default="admin",
        description="MongoDB database name",
    )
    
    # SMTP Email Server
    SMTP_HOST: str = Field(
        default="smtp.fxmail.ai",
        description="SMTP server hostname",
    )
    SMTP_PORT: int = Field(
        default=587,
        description="SMTP server port",
    )
    SMTP_USERNAME: str = Field(
        default="",
        description="SMTP username",
    )
    SMTP_PASSWORD: str = Field(
        default="",
        description="SMTP password",
    )
    SMTP_USE_TLS: bool = Field(
        default=True,
        description="Use TLS for SMTP",
    )
    
    # AWS (Optional - for file storage)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: str = ""
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text
    LOG_DIR: str = "./logs"
    
    # GrapheneOS / Device Flashing
    ADB_PATH: str = "/usr/local/bin/adb"
    FASTBOOT_PATH: str = "/usr/local/bin/fastboot"
    GRAPHENE_SOURCE_ROOT: str = ""
    GRAPHENE_BUNDLES_ROOT: str = Field(
        default="~/.graphene-installer/bundles",
        description="Root directory for GrapheneOS bundles",
    )
    APK_STORAGE_DIR: str = Field(
        default="~/.graphene-installer/apks",
        description="Directory for storing uploaded APK files",
    )
    SUPPORTED_CODENAMES: str = Field(
        default="cheetah,panther,raven,oriole,husky,shiba,akita,felix,tangorpro,lynx,bluejay,barbet,redfin",
        description="Comma-separated list of supported device codenames",
    )
    
    # Safety
    DRY_RUN_DEFAULT: bool = True
    SCRIPT_TIMEOUT_SEC: int = 1800
    ALLOW_ADVANCED_FASTBOOT: bool = False
    REQUIRE_TYPED_CONFIRMATION: bool = False
    
    # Build
    BUILD_ENABLE: bool = False
    BUILD_OUTPUT_DIR: str = ""
    BUILD_TIMEOUT_SEC: int = 14400
    
    @field_validator("CORS_ORIGINS")
    @classmethod
    def parse_cors_origins(cls, v: str) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in v.split(",") if origin.strip()]
    
    @field_validator("ALLOWED_HOSTS")
    @classmethod
    def parse_allowed_hosts(cls, v: str) -> List[str]:
        """Parse allowed hosts from comma-separated string"""
        return [host.strip() for host in v.split(",") if host.strip()]
    
    @property
    def supported_codenames_list(self) -> List[str]:
        """Parse supported codenames from comma-separated string"""
        return [c.strip() for c in self.SUPPORTED_CODENAMES.split(",") if c.strip()]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT.lower() == "development"


settings = Settings()

