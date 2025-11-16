"""Application settings and configuration management."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "gpt-4-turbo-preview"
    openai_embedding_model: str = "text-embedding-3-small"

    # Database Configuration
    database_url: str
    redis_url: str

    # Vector Store
    chroma_persist_directory: str = "./data/chroma"
    vector_store_collection: str = "bmo_learning_docs"

    # LangChain
    langchain_tracing_v2: bool = False
    langchain_api_key: str | None = None

    # Safety
    enable_constitutional_ai: bool = True
    enable_pii_detection: bool = True
    max_tokens_per_lesson: int = 500

    # Caching
    enable_llm_cache: bool = True
    cache_ttl_seconds: int = 3600

    # Rate Limiting
    rate_limit_per_minute: int = 60

    # CORS
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    # AWS Configuration (optional for local development)
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region: str = "us-east-1"

    # Application Configuration
    python_env: str = "development"
    log_level: str = "INFO"

    # External Services (optional)
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    slack_bot_token: str | None = None

    model_config = {
        "env_file": ".env",
        "case_sensitive": False
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
