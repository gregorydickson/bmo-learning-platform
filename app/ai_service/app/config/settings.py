"""Application settings and configuration management."""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Anthropic Configuration
    anthropic_api_key: str
    anthropic_model: str = "claude-haiku-4-5-20251001"
    ai_service_api_key: str = "dev_key"  # Default for dev, override in prod
    # Note: Using OpenAI embeddings for RAG (Anthropic doesn't provide embedding models)
    openai_api_key: str | None = None  # Optional: only needed if using OpenAI embeddings
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

    # Agent Configuration
    agent_temperature: float = 0.3
    agent_max_iterations: int = 5
    enable_agent_memory: bool = True
    memory_window_size: int = 10

    # AWS Configuration (optional for local development)
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region: str = "us-east-2"  # Matches production terraform region
    aws_endpoint_url: str | None = None  # For LocalStack override

    # LocalStack Configuration
    use_localstack: bool = False

    # S3 Configuration
    s3_documents_bucket: str = "bmo-learning-prod-documents"
    s3_backups_bucket: str = "bmo-learning-prod-backups"

    # Secrets Manager Configuration
    openai_secret_name: str | None = None
    database_secret_name: str | None = None
    redis_secret_name: str | None = None

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

    # ===================================================
    # Secrets Manager Integration
    # ===================================================

    def load_secret(
        self,
        setting_name: str,
        secret_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Load a setting value from AWS Secrets Manager.

        Falls back to environment variable if Secrets Manager is unavailable
        or disabled.

        Args:
            setting_name: Name of the setting (e.g., 'openai_api_key')
            secret_name: Secret name in Secrets Manager. If None, uses
                        <setting_name>_secret_name from settings

        Returns:
            Secret value or None if not found

        Example:
            settings = Settings()
            api_key = settings.load_secret('openai_api_key')
        """
        # Skip Secrets Manager if disabled
        if not self.use_localstack and not self.aws_endpoint_url:
            # Production mode but no AWS configured
            return getattr(self, setting_name, None)

        # Get secret name
        if secret_name is None:
            # Try to get from <setting_name>_secret_name attribute
            secret_name_attr = f"{setting_name}_secret_name"
            secret_name = getattr(self, secret_name_attr, None)

            if secret_name is None:
                logger.warning(
                    "No secret name configured for setting",
                    setting_name=setting_name
                )
                return getattr(self, setting_name, None)

        try:
            from app.config.secrets_manager import SecretsManagerClient

            client = SecretsManagerClient(
                endpoint_url=self.aws_endpoint_url,
                access_key_id=self.aws_access_key_id,
                secret_access_key=self.aws_secret_access_key,
                region=self.aws_region
            )

            result = client.get_secret(secret_name)

            logger.info(
                "Secret loaded from Secrets Manager",
                setting_name=setting_name,
                secret_name=secret_name
            )

            return result['secret_value']

        except Exception as e:
            logger.warning(
                "Failed to load secret from Secrets Manager, falling back to environment",
                setting_name=setting_name,
                secret_name=secret_name,
                error=str(e)
            )
            # Fallback to environment variable
            return getattr(self, setting_name, None)

    def load_secret_field(
        self,
        setting_name: str,
        field_name: str,
        secret_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Load a specific field from a JSON secret in Secrets Manager.

        Args:
            setting_name: Name of the setting (for logging/fallback)
            field_name: Field name within JSON secret
            secret_name: Secret name in Secrets Manager

        Returns:
            Field value or None if not found

        Example:
            settings = Settings()
            api_key = settings.load_secret_field(
                setting_name='database_credentials',
                field_name='password',
                secret_name='bmo-learning/prod/db-creds'
            )
        """
        # Get secret name if not provided
        if secret_name is None:
            secret_name_attr = f"{setting_name}_secret_name"
            secret_name = getattr(self, secret_name_attr, None)

            if secret_name is None:
                logger.warning(
                    "No secret name configured",
                    setting_name=setting_name
                )
                return getattr(self, setting_name, None)

        try:
            from app.config.secrets_manager import SecretsManagerClient

            client = SecretsManagerClient(
                endpoint_url=self.aws_endpoint_url,
                access_key_id=self.aws_access_key_id,
                secret_access_key=self.aws_secret_access_key,
                region=self.aws_region
            )

            result = client.get_secret_field(
                secret_name=secret_name,
                field_name=field_name
            )

            logger.info(
                "Secret field loaded from Secrets Manager",
                setting_name=setting_name,
                secret_name=secret_name,
                field_name=field_name
            )

            return result['field_value']

        except Exception as e:
            logger.warning(
                "Failed to load secret field, falling back to environment",
                setting_name=setting_name,
                field_name=field_name,
                error=str(e)
            )
            # Fallback to environment variable
            return getattr(self, setting_name, None)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
