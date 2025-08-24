import os
from typing import Optional, List
from pydantic import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # Database settings
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/suna_lite"
    
    # API Keys
    OPENAI_API_KEY: Optional[str] = None
    
    # CoexistAI settings
    COEXISTAI_BASE_URL: str = "http://coexistai:8000"
    COEXISTAI_API_KEY: str = ""
    
    # Runner settings
    RUNNER_BASE_URL: str = "http://runner:8080"
    
    # Agent settings
    MAX_ITERATIONS: int = 10
    TIMEOUT_SECONDS: int = 30
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Get settings singleton instance."""
    return Settings()

# For backward compatibility
settings = get_settings()