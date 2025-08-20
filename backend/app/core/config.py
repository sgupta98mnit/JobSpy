"""
Application configuration settings.

Manages environment variables and application settings using Pydantic.
"""

import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings configuration."""
    
    # Application
    PROJECT_NAME: str = "JobSpy Web API"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # API
    API_V1_STR: str = "/api/v1"
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # JobSpy Configuration
    DEFAULT_RESULTS_WANTED: int = 20
    MAX_RESULTS_WANTED: int = 100
    DEFAULT_DISTANCE: int = 50
    MAX_DISTANCE: int = 200
    
    # Cache settings (for future use)
    CACHE_TTL_SECONDS: int = 300  # 5 minutes
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()