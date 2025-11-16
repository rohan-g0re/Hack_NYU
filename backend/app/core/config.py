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
    LM_STUDIO_DEFAULT_MODEL: str = "qwen3-1.7b"
    LM_STUDIO_TIMEOUT: int = 30  # seconds
    
    # LLM Request Configuration
    LLM_MAX_RETRIES: int = 3
    LLM_RETRY_DELAY: int = 2  # seconds, base for exponential backoff
    LLM_DEFAULT_TEMPERATURE: float = 0.0  # Phase 2: deterministic by default
    LLM_DEFAULT_MAX_TOKENS: int = 256  # Phase 2: constrained generation
    
    # OpenRouter Configuration
    LLM_ENABLE_OPENROUTER: bool = False
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    
    # Phase 2: Negotiation Configuration
    MAX_NEGOTIATION_ROUNDS: int = 10
    PARALLEL_SELLER_LIMIT: int = 3  # Max concurrent seller responses
    
    # Phase 3: Session Management & Persistence
    MAX_SELLERS_PER_SESSION: int = 10
    SESSION_CLEANUP_HOURS: int = 1  # TTL for in-memory cache
    NEGOTIATION_TIMEOUT_MINUTES: int = 30
    
    # Phase 3: Logging & Retention
    LOG_RETENTION_DAYS: int = 7
    LOGS_DIR: str = "data/logs/sessions"
    AUTO_SAVE_NEGOTIATIONS: bool = True
    
    # Phase 4: Streaming
    SSE_HEARTBEAT_INTERVAL: int = 15  # seconds
    SSE_RETRY_TIMEOUT: int = 5  # seconds
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./data/logs/app.log"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Singleton instance
settings = Settings()

