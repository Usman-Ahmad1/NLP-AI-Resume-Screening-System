"""
Simplified configuration management for the Resume Screener application.
"""

from typing import List
import os
from pathlib import Path


class Settings:
    """Application settings loaded from environment variables."""
    
    # App metadata
    APP_NAME: str = "Resume Screener"
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # API configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "sqlite:///./data/resume_screener.db"
    
    # Ollama
    OLLAMA_ENABLED: bool = False
    OLLAMA_MODEL: str = "llama2"
    OLLAMA_API_BASE: str = "http://localhost:11434"
    
    # Embedding model
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    # File upload limits
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".txt"]
    
    # Security
    SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:8501", "http://localhost:3000"]
    
    def __init__(self):
        # Load from environment variables if present
        for key in dir(self):
            if key.isupper():
                env_value = os.getenv(key)
                if env_value is not None:
                    # Parse lists from comma-separated strings
                    if key in ['ALLOWED_EXTENSIONS', 'CORS_ORIGINS']:
                        setattr(self, key, [x.strip() for x in env_value.split(',') if x.strip()])
                    elif key in ['APP_ENV', 'LOG_LEVEL']:
                        setattr(self, key, env_value)
                    elif key in ['DEBUG']:
                        setattr(self, key, env_value.lower() == 'true')
                    else:
                        setattr(self, key, env_value)
        
        # Create database directory if it doesn't exist
        db_path = self.DATABASE_URL.replace("sqlite:///", "")
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)


# Global settings instance
settings = Settings()