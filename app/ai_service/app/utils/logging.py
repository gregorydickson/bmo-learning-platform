"""Structured logging configuration."""
import structlog
from typing import Any


def configure_logging():
    """Configure structured logging for the application."""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def log_llm_call(prompt: str, response: str, metadata: dict[str, Any]):
    """Log LLM API call with metadata."""
    logger = structlog.get_logger()
    logger.info(
        "llm_call",
        prompt_length=len(prompt),
        response_length=len(response),
        **metadata
    )
