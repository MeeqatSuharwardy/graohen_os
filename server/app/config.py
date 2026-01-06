"""
Server Configuration
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # Security
    API_KEY: str = ""
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # Bundle Storage
    BUNDLES_ROOT: str = "/Users/vt_dev/upwork_graphene/graohen_os/bundles"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

