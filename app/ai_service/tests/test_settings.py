"""Tests for application settings."""
import pytest
import os
from app.config.settings import Settings, get_settings


class TestSettings:
    """Test suite for application settings."""

    def test_settings_initialization(self, monkeypatch):
        """Test settings can be initialized with environment variables."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        settings = Settings()

        assert settings.openai_api_key == "sk-test-key"
        assert settings.database_url == "postgresql://localhost/test"
        assert settings.redis_url == "redis://localhost:6379/0"

    def test_settings_defaults(self, monkeypatch):
        """Test default values are set correctly."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        settings = Settings()

        assert settings.openai_model == "gpt-4-turbo-preview"
        assert settings.openai_embedding_model == "text-embedding-3-small"
        assert settings.enable_constitutional_ai is True
        assert settings.enable_pii_detection is True
        assert settings.max_tokens_per_lesson == 500
        assert settings.enable_llm_cache is True
        assert settings.cache_ttl_seconds == 3600
        assert settings.rate_limit_per_minute == 60

    def test_settings_optional_fields(self, monkeypatch):
        """Test optional fields can be None."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        settings = Settings()

        assert settings.langchain_api_key is None
        assert settings.aws_access_key_id is None
        assert settings.aws_secret_access_key is None
        assert settings.twilio_account_sid is None
        assert settings.twilio_auth_token is None
        assert settings.slack_bot_token is None

    def test_settings_required_fields_missing(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises((ValueError, Exception)):
            Settings()

    def test_settings_case_insensitive(self, monkeypatch):
        """Test environment variables are case insensitive."""
        monkeypatch.setenv("openai_api_key", "sk-test-key")
        monkeypatch.setenv("database_url", "postgresql://localhost/test")
        monkeypatch.setenv("redis_url", "redis://localhost:6379/0")

        settings = Settings()

        assert settings.openai_api_key == "sk-test-key"

    def test_get_settings_cached(self, monkeypatch):
        """Test that get_settings returns cached instance."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-1")
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        settings1 = get_settings()
        settings2 = get_settings()

        # Should return same cached instance
        assert settings1 is settings2

    def test_chroma_persist_directory_default(self, monkeypatch):
        """Test Chroma persistence directory default."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        settings = Settings()

        assert settings.chroma_persist_directory == "./data/chroma"
        assert settings.vector_store_collection == "bmo_learning_docs"

    def test_allowed_origins_default(self, monkeypatch):
        """Test CORS allowed origins default."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        settings = Settings()

        assert isinstance(settings.allowed_origins, list)
        assert "http://localhost:3000" in settings.allowed_origins

    def test_aws_region_default(self, monkeypatch):
        """Test AWS region default value."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        settings = Settings()

        assert settings.aws_region == "us-east-1"

    def test_python_env_default(self, monkeypatch):
        """Test Python environment default."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        settings = Settings()

        assert settings.python_env == "development"

    def test_log_level_default(self, monkeypatch):
        """Test log level default."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        settings = Settings()

        assert settings.log_level == "INFO"

    def test_settings_can_override_defaults(self, monkeypatch):
        """Test that environment variables override defaults."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4")
        monkeypatch.setenv("MAX_TOKENS_PER_LESSON", "1000")
        monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "120")

        settings = Settings()

        assert settings.openai_model == "gpt-4"
        assert settings.max_tokens_per_lesson == 1000
        assert settings.rate_limit_per_minute == 120

    def test_langchain_tracing_disabled_by_default(self, monkeypatch):
        """Test LangChain tracing is disabled by default."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        settings = Settings()

        assert settings.langchain_tracing_v2 is False
