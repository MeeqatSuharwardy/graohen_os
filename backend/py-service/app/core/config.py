"""Application Configuration"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    
    # Application
    APP_NAME: str = "FastAPI Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/fastapi_db",
        description="PostgreSQL database URL",
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
        default="change-this-secret-key-in-production",
        description="Secret key for JWT tokens",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    
    # Email
    EXTERNAL_HTTPS_BASE_URL: str = Field(
        default="https://fxmail.ai",
        description="Base URL for external email links",
    )
    
    # AWS (Optional)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: str = ""
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text
    
    # GrapheneOS / Device Flashing
    ADB_PATH: str = "/usr/local/bin/adb"
    FASTBOOT_PATH: str = "/usr/local/bin/fastboot"
    GRAPHENE_BUNDLES_ROOT: str = Field(
        default="~/.graphene-installer/bundles",
        description="Root directory for GrapheneOS bundles",
    )
    SUPPORTED_CODENAMES: str = Field(
        default="cheetah,panther,raven,oriole,husky,shiba,akita,felix,tangorpro,lynx,bluejay,barbet,redfin",
        description="Comma-separated list of supported device codenames",
    )
    REQUIRE_TYPED_CONFIRMATION: bool = Field(
        default=False,
        description="Require typed confirmation for flash operations",
    )
    SCRIPT_TIMEOUT_SEC: int = Field(
        default=1800,
        description="Timeout for flash scripts in seconds",
    )
    
    @property
    def supported_codenames_list(self) -> List[str]:
        """Parse supported codenames from comma-separated string"""
        return [c.strip() for c in self.SUPPORTED_CODENAMES.split(",") if c.strip()]
    
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
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT.lower() == "development"


# Global settings instance
settings = Settings()

