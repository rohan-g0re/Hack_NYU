"""
Application configuration using pydantic-settings.

WHAT: Centralized config from environment variables
WHY: Type-safe, validated config with sensible defaults
HOW: Pydantic BaseSettings reads from .env and environment
"""

from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    # App metadata
    APP_NAME: str = "Multi-Agent Marketplace"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "sqlite:///./data/marketplace.db"
    
    # LLM Provider Selection
    LLM_PROVIDER: Literal["lm_studio", "openrouter"] = "lm_studio"
    
    # LM Studio Configuration
    LM_STUDIO_BASE_URL: str = "http://localhost:1234/v1"
    LM_STUDIO_DEFAULT_MODEL: str = "llama-3-8b-instruct"
    LM_STUDIO_TIMEOUT: int = 30  # seconds
    
    # LLM Request Configuration
    LLM_MAX_RETRIES: int = 3
    LLM_RETRY_DELAY: int = 2  # seconds, base for exponential backoff
    LLM_DEFAULT_TEMPERATURE: float = 0.7
    LLM_DEFAULT_MAX_TOKENS: int = 500
    
    # Fast Dev Mode Configuration (optional overrides)
    LM_STUDIO_FAST_TIMEOUT: int | None = None  # If None, defaults to 12 in fast mode (vs 30s normal)
    LLM_FAST_MAX_RETRIES: int | None = None  # If None, defaults to 1 in fast mode (vs 3 normal)
    LLM_FAST_RETRY_DELAY: int | None = None  # If None, defaults to 1 in fast mode (vs 2 normal)
    
    # OpenRouter Configuration
    LLM_ENABLE_OPENROUTER: bool = False
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS string to list."""
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return self.CORS_ORIGINS if isinstance(self.CORS_ORIGINS, list) else []
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./data/logs/app.log"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Singleton instance
settings = Settings()

