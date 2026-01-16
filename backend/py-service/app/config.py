"""Unified Application Configuration - Merges FastAPI and GrapheneOS settings"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import List


class Settings(BaseSettings):
    """Unified application settings for FastAPI backend with GrapheneOS flashing support"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
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
    PY_HOST: str = "127.0.0.1"
    PY_PORT: int = 17890
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_HOSTS: str = "localhost,127.0.0.1,os.fxmail.ai,drive.fxmail.ai"
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/grapheneos_db",
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
        default="change-this-secret-key-in-production-use-long-random-string",
        description="Secret key for JWT tokens",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS - Allow localhost for development and production domains
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:5174,https://os.fxmail.ai,https://drive.fxmail.ai,https://fxmail.ai"
    
    # Email (for encrypted email service)
    EMAIL_DOMAIN: str = Field(
        default="fxmail.ai",
        description="Email domain for generating email addresses",
    )
    EXTERNAL_HTTPS_BASE_URL: str = Field(
        default="https://fxmail.ai",
        description="Base URL for external email links",
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

