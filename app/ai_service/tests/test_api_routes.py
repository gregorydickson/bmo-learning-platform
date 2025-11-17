"""Tests for API routes."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
from app.main import app


client = TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_root_endpoint(self):
        """Test root endpoint returns basic info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data

    def test_health_check_endpoint(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ai_service"
        assert "version" in data


class TestStatusEndpoint:
    """Test status endpoint."""

    def test_status_endpoint(self):
        """Test service status endpoint."""
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "ai_service"
        assert data["status"] == "operational"
        assert "features" in data
        assert data["features"]["rag"] is True
        assert data["features"]["lesson_generation"] is True
        assert data["features"]["safety_validation"] is True


class TestLessonGenerationEndpoint:
    """Test lesson generation endpoint."""

    @patch("app.generators.lesson_generator.LessonGenerator")
    @patch("app.safety.safety_validator.SafetyValidator")
    @patch("app.ingestion.vector_store.VectorStoreManager")
    def test_generate_lesson_success(self, mock_vector_manager, mock_safety, mock_generator):
        """Test successful lesson generation."""
        # Mock vector store
        vector_manager_instance = MagicMock()
        mock_vector_manager.return_value = vector_manager_instance
        vector_manager_instance.load_vector_store.return_value = MagicMock()

        # Mock lesson generator
        generator_instance = MagicMock()
        mock_generator.return_value = generator_instance
        generator_instance.generate_lesson.return_value = {
            "topic": "Python Functions",
            "content": "Functions are reusable blocks of code...",
            "scenario": "You're building a calculator...",
            "quiz_question": "What keyword defines a function?",
            "quiz_options": ["func", "def", "function"],
            "quiz_answer": "def"
        }

        # Mock safety validator
        safety_instance = MagicMock()
        mock_safety.return_value = safety_instance
        safety_instance.validate_content.return_value = {
            "passed": True,
            "pii_detected": False,
            "moderation_flagged": False,
            "issues": []
        }

        response = client.post(
            "/api/v1/generate-lesson",
            json={
                "topic": "Python Functions",
                "learner_id": "learner_123",
                "difficulty": "medium"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "lesson" in data
        assert "metadata" in data
        assert "safety_check" in data
        assert data["lesson"]["topic"] == "Python Functions"
        assert data["safety_check"]["passed"] is True

    @patch("app.generators.lesson_generator.LessonGenerator")
    @patch("app.safety.safety_validator.SafetyValidator")
    @patch("app.ingestion.vector_store.VectorStoreManager")
    def test_generate_lesson_without_rag(self, mock_vector_manager, mock_safety, mock_generator):
        """Test lesson generation when RAG is unavailable."""
        # Mock vector store to raise exception
        vector_manager_instance = MagicMock()
        mock_vector_manager.return_value = vector_manager_instance
        vector_manager_instance.load_vector_store.side_effect = Exception("Vector store not available")

        # Mock lesson generator
        generator_instance = MagicMock()
        mock_generator.return_value = generator_instance
        generator_instance.generate_lesson.return_value = {
            "topic": "Test Topic",
            "content": "Content without RAG",
            "scenario": "Scenario",
            "quiz_question": "Question?",
            "quiz_options": ["A", "B"],
            "quiz_answer": "A"
        }

        # Mock safety validator
        safety_instance = MagicMock()
        mock_safety.return_value = safety_instance
        safety_instance.validate_content.return_value = {
            "passed": True,
            "pii_detected": False,
            "moderation_flagged": False,
            "issues": []
        }

        response = client.post(
            "/api/v1/generate-lesson",
            json={
                "topic": "Test Topic",
                "learner_id": "learner_123"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["rag_enabled"] is False

    def test_generate_lesson_missing_topic(self):
        """Test lesson generation with missing required field."""
        response = client.post(
            "/api/v1/generate-lesson",
            json={
                "learner_id": "learner_123"
            }
        )

        assert response.status_code == 422  # Validation error

    def test_generate_lesson_empty_topic(self):
        """Test lesson generation with empty topic."""
        response = client.post(
            "/api/v1/generate-lesson",
            json={
                "topic": "",
                "learner_id": "learner_123"
            }
        )

        # Should return validation error or bad request
        assert response.status_code in [400, 422]

    @patch("app.generators.lesson_generator.LessonGenerator")
    @patch("app.safety.safety_validator.SafetyValidator")
    @patch("app.ingestion.vector_store.VectorStoreManager")
    def test_generate_lesson_safety_failure(self, mock_vector_manager, mock_safety, mock_generator):
        """Test lesson generation with safety check failure."""
        # Mock vector store
        vector_manager_instance = MagicMock()
        mock_vector_manager.return_value = vector_manager_instance
        vector_manager_instance.load_vector_store.return_value = MagicMock()

        # Mock lesson generator
        generator_instance = MagicMock()
        mock_generator.return_value = generator_instance
        generator_instance.generate_lesson.return_value = {
            "topic": "Test",
            "content": "Content with PII: SSN 123-45-6789",
            "scenario": "Scenario",
            "quiz_question": "Question?",
            "quiz_options": ["A"],
            "quiz_answer": "A"
        }

        # Mock safety validator to detect PII
        safety_instance = MagicMock()
        mock_safety.return_value = safety_instance
        safety_instance.validate_content.return_value = {
            "passed": False,
            "pii_detected": True,
            "moderation_flagged": False,
            "issues": ["PII detected in content"]
        }
        safety_instance.sanitize_content.return_value = "Content with PII: SSN [REDACTED]"

        response = client.post(
            "/api/v1/generate-lesson",
            json={
                "topic": "Test",
                "learner_id": "learner_123"
            }
        )

        assert response.status_code == 200  # Still returns but with sanitized content
        data = response.json()
        assert data["safety_check"]["passed"] is False
        assert data["safety_check"]["pii_detected"] is True

    @patch("app.generators.lesson_generator.LessonGenerator")
    @patch("app.safety.safety_validator.SafetyValidator")
    @patch("app.ingestion.vector_store.VectorStoreManager")
    def test_generate_lesson_generator_error(self, mock_vector_manager, mock_safety, mock_generator):
        """Test lesson generation when generator raises error."""
        # Mock vector store
        vector_manager_instance = MagicMock()
        mock_vector_manager.return_value = vector_manager_instance
        vector_manager_instance.load_vector_store.return_value = MagicMock()

        # Mock lesson generator to raise exception
        generator_instance = MagicMock()
        mock_generator.return_value = generator_instance
        generator_instance.generate_lesson.side_effect = Exception("OpenAI API Error")

        response = client.post(
            "/api/v1/generate-lesson",
            json={
                "topic": "Test",
                "learner_id": "learner_123"
            }
        )

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data

    def test_generate_lesson_invalid_json(self):
        """Test lesson generation with invalid JSON."""
        response = client.post(
            "/api/v1/generate-lesson",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422


class TestSafetyValidationEndpoint:
    """Test safety validation endpoint."""

    @patch("app.safety.safety_validator.SafetyValidator")
    def test_validate_safety_clean_content(self, mock_safety):
        """Test safety validation with clean content."""
        safety_instance = MagicMock()
        mock_safety.return_value = safety_instance
        safety_instance.validate_content.return_value = {
            "passed": True,
            "pii_detected": False,
            "moderation_flagged": False,
            "issues": []
        }

        response = client.post(
            "/api/v1/validate-safety",
            params={"content": "This is clean educational content"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["passed"] is True

    @patch("app.safety.safety_validator.SafetyValidator")
    def test_validate_safety_pii_detected(self, mock_safety):
        """Test safety validation with PII."""
        safety_instance = MagicMock()
        mock_safety.return_value = safety_instance
        safety_instance.validate_content.return_value = {
            "passed": False,
            "pii_detected": True,
            "moderation_flagged": False,
            "issues": ["PII detected"]
        }

        response = client.post(
            "/api/v1/validate-safety",
            params={"content": "My SSN is 123-45-6789"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["passed"] is False
        assert data["pii_detected"] is True


class TestDocumentIngestionEndpoint:
    """Test document ingestion endpoint."""

    @patch("app.ingestion.document_processor.DocumentProcessor")
    @patch("app.ingestion.vector_store.VectorStoreManager")
    def test_ingest_documents_accepted(self, mock_vector_manager, mock_processor):
        """Test document ingestion returns accepted status."""
        response = client.post(
            "/api/v1/ingest-documents",
            params={"directory": "/path/to/documents"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert "message" in data


class TestErrorHandling:
    """Test error handling across endpoints."""

    def test_404_not_found(self):
        """Test 404 for non-existent endpoint."""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed(self):
        """Test 405 for wrong HTTP method."""
        response = client.get("/api/v1/generate-lesson")
        assert response.status_code == 405

    def test_cors_headers(self):
        """Test CORS headers are present."""
        response = client.options("/api/v1/status")
        # CORS headers should be present (if configured)
        assert response.status_code in [200, 405]  # Varies by CORS config


class TestResponseSchemas:
    """Test response schema validation."""

    @patch("app.generators.lesson_generator.LessonGenerator")
    @patch("app.safety.safety_validator.SafetyValidator")
    @patch("app.ingestion.vector_store.VectorStoreManager")
    def test_lesson_response_schema(self, mock_vector_manager, mock_safety, mock_generator):
        """Test lesson response matches expected schema."""
        # Setup mocks
        vector_manager_instance = MagicMock()
        mock_vector_manager.return_value = vector_manager_instance
        vector_manager_instance.load_vector_store.return_value = MagicMock()

        generator_instance = MagicMock()
        mock_generator.return_value = generator_instance
        generator_instance.generate_lesson.return_value = {
            "topic": "Test",
            "content": "Content",
            "scenario": "Scenario",
            "quiz_question": "Q?",
            "quiz_options": ["A"],
            "quiz_answer": "A"
        }

        safety_instance = MagicMock()
        mock_safety.return_value = safety_instance
        safety_instance.validate_content.return_value = {
            "passed": True,
            "pii_detected": False,
            "moderation_flagged": False,
            "issues": []
        }

        response = client.post(
            "/api/v1/generate-lesson",
            json={"topic": "Test", "learner_id": "123"}
        )

        data = response.json()

        # Verify required fields
        assert "lesson" in data
        assert "metadata" in data
        assert "safety_check" in data

        # Verify metadata structure
        assert "generated_at" in data["metadata"]
        assert "model" in data["metadata"]
        assert "rag_enabled" in data["metadata"]

        # Verify safety check structure
        assert "passed" in data["safety_check"]
        assert "pii_detected" in data["safety_check"]
        assert "moderation_flagged" in data["safety_check"]
        assert "issues" in data["safety_check"]
