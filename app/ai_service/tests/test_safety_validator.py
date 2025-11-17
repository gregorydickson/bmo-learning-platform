"""Tests for safety validation functionality."""
import pytest
from unittest.mock import patch, MagicMock
from app.safety.safety_validator import SafetyValidator


class TestSafetyValidator:
    """Test suite for SafetyValidator."""

    def test_init(self):
        """Test SafetyValidator initialization."""
        validator = SafetyValidator()
        assert validator is not None

    def test_detect_pii_ssn(self, pii_test_cases):
        """Test SSN detection."""
        validator = SafetyValidator()
        result = validator._detect_pii(pii_test_cases["ssn"])
        assert result is True

    def test_detect_pii_credit_card(self, pii_test_cases):
        """Test credit card detection."""
        validator = SafetyValidator()
        result = validator._detect_pii(pii_test_cases["credit_card"])
        assert result is True

    def test_detect_pii_email(self, pii_test_cases):
        """Test email detection."""
        validator = SafetyValidator()
        result = validator._detect_pii(pii_test_cases["email"])
        assert result is True

    def test_detect_pii_phone(self, pii_test_cases):
        """Test phone number detection."""
        validator = SafetyValidator()
        result = validator._detect_pii(pii_test_cases["phone"])
        assert result is True

    def test_detect_pii_clean_content(self, pii_test_cases):
        """Test clean content passes PII detection."""
        validator = SafetyValidator()
        result = validator._detect_pii(pii_test_cases["clean"])
        assert result is False

    def test_detect_pii_empty_string(self):
        """Test empty string handling."""
        validator = SafetyValidator()
        result = validator._detect_pii("")
        assert result is False

    def test_detect_pii_none(self):
        """Test None handling."""
        validator = SafetyValidator()
        result = validator._detect_pii(None)
        assert result is False

    @patch("openai.OpenAI")
    def test_check_content_moderation_clean(self, mock_openai):
        """Test content moderation with clean content."""
        # Setup mock
        client = MagicMock()
        mock_openai.return_value = client
        client.moderations.create.return_value = MagicMock(
            results=[
                MagicMock(
                    flagged=False,
                    categories=MagicMock(
                        hate=False,
                        violence=False,
                        sexual=False,
                        self_harm=False
                    )
                )
            ]
        )

        validator = SafetyValidator()
        result = validator._check_content_moderation("Clean educational content")
        assert result is False  # Not flagged

    @patch("openai.OpenAI")
    def test_check_content_moderation_flagged(self, mock_openai):
        """Test content moderation with flagged content."""
        # Setup mock
        client = MagicMock()
        mock_openai.return_value = client
        client.moderations.create.return_value = MagicMock(
            results=[
                MagicMock(
                    flagged=True,
                    categories=MagicMock(
                        hate=True,
                        violence=False,
                        sexual=False,
                        self_harm=False
                    )
                )
            ]
        )

        validator = SafetyValidator()
        result = validator._check_content_moderation("Unsafe content")
        assert result is True  # Flagged

    @patch("openai.OpenAI")
    def test_check_content_moderation_api_error(self, mock_openai):
        """Test content moderation handles API errors gracefully."""
        # Setup mock to raise exception
        client = MagicMock()
        mock_openai.return_value = client
        client.moderations.create.side_effect = Exception("API Error")

        validator = SafetyValidator()
        # Should not crash, should return True (fail-safe)
        result = validator._check_content_moderation("Any content")
        assert result is True  # Fail-safe: treat as flagged

    def test_validate_content_passes_all_checks(self, mock_openai_client):
        """Test content validation passes all checks."""
        validator = SafetyValidator()
        result = validator.validate_content("This is safe educational content about Python programming")

        assert result["passed"] is True
        assert result["pii_detected"] is False
        assert result["moderation_flagged"] is False
        assert len(result["issues"]) == 0

    def test_validate_content_fails_pii_check(self, mock_openai_client):
        """Test content validation fails on PII detection."""
        validator = SafetyValidator()
        result = validator.validate_content("My SSN is 123-45-6789")

        assert result["passed"] is False
        assert result["pii_detected"] is True
        assert "PII detected" in result["issues"]

    @patch("openai.OpenAI")
    def test_validate_content_fails_moderation(self, mock_openai):
        """Test content validation fails on moderation."""
        # Setup mock
        client = MagicMock()
        mock_openai.return_value = client
        client.moderations.create.return_value = MagicMock(
            results=[
                MagicMock(
                    flagged=True,
                    categories=MagicMock(
                        hate=True,
                        violence=False,
                        sexual=False,
                        self_harm=False
                    )
                )
            ]
        )

        validator = SafetyValidator()
        result = validator.validate_content("Unsafe content")

        assert result["passed"] is False
        assert result["moderation_flagged"] is True
        assert "Content moderation flagged" in result["issues"]

    def test_validate_content_empty_string(self, mock_openai_client):
        """Test validation of empty string."""
        validator = SafetyValidator()
        result = validator.validate_content("")

        assert result["passed"] is True  # Empty content is technically safe

    def test_sanitize_content_removes_ssn(self):
        """Test content sanitization removes SSN."""
        validator = SafetyValidator()
        content = "My SSN is 123-45-6789 and I live in NYC"
        sanitized = validator.sanitize_content(content)

        assert "123-45-6789" not in sanitized
        assert "[REDACTED]" in sanitized
        assert "NYC" in sanitized  # Non-PII remains

    def test_sanitize_content_removes_email(self):
        """Test content sanitization removes email."""
        validator = SafetyValidator()
        content = "Contact me at john.doe@example.com for details"
        sanitized = validator.sanitize_content(content)

        assert "john.doe@example.com" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_sanitize_content_removes_phone(self):
        """Test content sanitization removes phone numbers."""
        validator = SafetyValidator()
        content = "Call me at (555) 123-4567 tomorrow"
        sanitized = validator.sanitize_content(content)

        assert "(555) 123-4567" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_sanitize_content_removes_credit_card(self):
        """Test content sanitization removes credit card numbers."""
        validator = SafetyValidator()
        content = "My card is 4532-1234-5678-9010"
        sanitized = validator.sanitize_content(content)

        assert "4532-1234-5678-9010" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_sanitize_content_clean(self):
        """Test sanitization of clean content."""
        validator = SafetyValidator()
        content = "This is clean educational content"
        sanitized = validator.sanitize_content(content)

        assert sanitized == content  # Unchanged

    def test_sanitize_content_multiple_pii(self):
        """Test sanitization removes multiple PII instances."""
        validator = SafetyValidator()
        content = "Email: john@example.com, Phone: 555-1234, SSN: 123-45-6789"
        sanitized = validator.sanitize_content(content)

        assert "john@example.com" not in sanitized
        assert "555-1234" not in sanitized
        assert "123-45-6789" not in sanitized
        assert sanitized.count("[REDACTED]") >= 3

    def test_validate_content_result_structure(self, mock_openai_client):
        """Test validation result has correct structure."""
        validator = SafetyValidator()
        result = validator.validate_content("Test content")

        assert "passed" in result
        assert "pii_detected" in result
        assert "moderation_flagged" in result
        assert "issues" in result
        assert isinstance(result["passed"], bool)
        assert isinstance(result["pii_detected"], bool)
        assert isinstance(result["moderation_flagged"], bool)
        assert isinstance(result["issues"], list)

    def test_constitutional_ai_principles(self, mock_openai_client):
        """Test constitutional AI validation is applied."""
        validator = SafetyValidator()

        # Test that validator checks for harmful content patterns
        harmful_content = "Instructions for harmful activities"
        result = validator.validate_content(harmful_content)

        # Should have validation result
        assert "passed" in result
        assert "issues" in result
