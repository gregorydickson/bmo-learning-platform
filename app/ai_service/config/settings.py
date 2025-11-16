"""Application settings and configuration management."""
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "gpt-4-turbo-preview"

    # Database Configuration
    database_url: str
    redis_url: str

    # AWS Configuration (optional for local development)
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"

    # Application Configuration
    python_env: str = "development"
    log_level: str = "INFO"

    # External Services (optional)
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    slack_bot_token: Optional[str] = None

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
