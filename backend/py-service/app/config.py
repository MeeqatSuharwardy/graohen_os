from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Server
    PY_HOST: str = "127.0.0.1"
    PY_PORT: int = 17890
    
    # Tools
    ADB_PATH: str = "/usr/local/bin/adb"
    FASTBOOT_PATH: str = "/usr/local/bin/fastboot"
    
    # GrapheneOS Paths
    GRAPHENE_SOURCE_ROOT: str = ""
    GRAPHENE_BUNDLES_ROOT: str = ""
    
    # Logging
    LOG_DIR: str = "./logs"
    
    # Supported Devices
    SUPPORTED_CODENAMES: str = "cheetah,panther,raven,oriole,husky,shiba,akita,felix,tangorpro,lynx,bluejay,barbet,redfin"
    
    # Safety
    DRY_RUN_DEFAULT: bool = True
    SCRIPT_TIMEOUT_SEC: int = 1800
    ALLOW_ADVANCED_FASTBOOT: bool = False
    REQUIRE_TYPED_CONFIRMATION: bool = True
    
    # Build
    BUILD_ENABLE: bool = False
    BUILD_OUTPUT_DIR: str = ""
    BUILD_TIMEOUT_SEC: int = 14400
    
    @property
    def supported_codenames_list(self) -> List[str]:
        return [c.strip() for c in self.SUPPORTED_CODENAMES.split(",") if c.strip()]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

