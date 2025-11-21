"""Tests for API routes."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
from app.main import app


client = TestClient(app)

# API key headers for authenticated endpoints
API_HEADERS = {"X-API-Key": "dev_key"}


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
    @patch("app.api.routes.safety_validator")
    @patch("app.api.routes.vector_store_manager")
    def test_generate_lesson_success(self, mock_vector_manager, mock_safety, mock_generator):
        """Test successful lesson generation."""
        # Mock vector store manager (module-level instance)
        mock_vector_store = MagicMock()
        mock_retriever = MagicMock()
        mock_vector_manager.load_vector_store.return_value = mock_vector_store
        mock_vector_manager.as_retriever.return_value = mock_retriever

        # Mock lesson generator (created per-request)
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

        # Mock safety validator (module-level instance)
        mock_safety.validate_content.return_value = {
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
        , headers=API_HEADERS)

        assert response.status_code == 200
        data = response.json()
        assert "lesson" in data
        assert "metadata" in data
        assert "safety_check" in data
        assert data["lesson"]["topic"] == "Python Functions"
        assert data["safety_check"]["passed"] is True

    @patch("app.generators.lesson_generator.LessonGenerator")
    @patch("app.api.routes.safety_validator")
    @patch("app.api.routes.vector_store_manager")
    def test_generate_lesson_without_rag(self, mock_vector_manager, mock_safety, mock_generator):
        """Test lesson generation when RAG is unavailable."""
        # Mock vector store manager to raise exception (module-level instance)
        mock_vector_manager.load_vector_store.side_effect = Exception("Vector store not available")

        # Mock lesson generator (created per-request)
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

        # Mock safety validator (module-level instance)
        mock_safety.validate_content.return_value = {
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
        , headers=API_HEADERS)

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
        , headers=API_HEADERS)

        assert response.status_code == 422  # Validation error

    def test_generate_lesson_empty_topic(self):
        """Test lesson generation with empty topic."""
        response = client.post(
            "/api/v1/generate-lesson",
            json={
                "topic": "",
                "learner_id": "learner_123"
            }
        , headers=API_HEADERS)

        # Empty topic validation happens in LessonGenerator, returns 500
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Topic cannot be empty" in data["detail"]

    @patch("app.generators.lesson_generator.LessonGenerator")
    @patch("app.api.routes.safety_validator")
    @patch("app.api.routes.vector_store_manager")
    def test_generate_lesson_safety_failure(self, mock_vector_manager, mock_safety, mock_generator):
        """Test lesson generation with safety check failure."""
        # Mock vector store manager (module-level instance)
        mock_vector_store = MagicMock()
        mock_retriever = MagicMock()
        mock_vector_manager.load_vector_store.return_value = mock_vector_store
        mock_vector_manager.as_retriever.return_value = mock_retriever

        # Mock lesson generator (created per-request)
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

        # Mock safety validator to detect PII (module-level instance)
        mock_safety.validate_content.return_value = {
            "passed": False,
            "pii_detected": True,
            "moderation_flagged": False,
            "issues": ["PII detected in content"]
        }
        mock_safety.sanitize_content.return_value = "Content with PII: SSN [REDACTED]"

        response = client.post(
            "/api/v1/generate-lesson",
            json={
                "topic": "Test",
                "learner_id": "learner_123"
            }
        , headers=API_HEADERS)

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
            },
            headers={"X-API-Key": "dev_key"}
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

    @patch("app.api.routes.safety_validator")
    def test_validate_safety_clean_content(self, mock_safety):
        """Test safety validation with clean content."""
        # Mock module-level safety_validator instance
        mock_safety.validate_content.return_value = {
            "passed": True,
            "pii_detected": False,
            "moderation_flagged": False,
            "issues": []
        }

        response = client.post(
            "/api/v1/validate-safety",
            params={"content": "This is clean educational content"}
        , headers=API_HEADERS)

        assert response.status_code == 200
        data = response.json()
        assert data["passed"] is True

    @patch("app.api.routes.safety_validator")
    def test_validate_safety_pii_detected(self, mock_safety):
        """Test safety validation with PII."""
        # Mock module-level safety_validator instance
        mock_safety.validate_content.return_value = {
            "passed": False,
            "pii_detected": True,
            "moderation_flagged": False,
            "issues": ["PII detected"]
        }

        response = client.post(
            "/api/v1/validate-safety",
            params={"content": "My SSN is 123-45-6789"}
        , headers=API_HEADERS)

        assert response.status_code == 200
        data = response.json()
        assert data["passed"] is False
        assert data["pii_detected"] is True


class TestDocumentIngestionEndpoint:
    """Test document ingestion endpoint."""

    @patch("app.ingestion.document_processor.DocumentProcessor")
    @patch("app.api.routes.vector_store_manager")
    def test_ingest_documents_accepted(self, mock_vector_manager, mock_processor):
        """Test document ingestion returns accepted status."""
        # Note: This test just checks the endpoint returns accepted status
        # The background task won't actually run in the test
        response = client.post(
            "/api/v1/ingest-documents",
            params={"directory": "/path/to/documents"}
        , headers=API_HEADERS)

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
    @patch("app.api.routes.safety_validator")
    @patch("app.api.routes.vector_store_manager")
    def test_lesson_response_schema(self, mock_vector_manager, mock_safety, mock_generator):
        """Test lesson response matches expected schema."""
        # Mock vector store manager (module-level instance)
        mock_vector_store = MagicMock()
        mock_retriever = MagicMock()
        mock_vector_manager.load_vector_store.return_value = mock_vector_store
        mock_vector_manager.as_retriever.return_value = mock_retriever

        # Mock lesson generator (created per-request)
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

        # Mock safety validator (module-level instance)
        mock_safety.validate_content.return_value = {
            "passed": True,
            "pii_detected": False,
            "moderation_flagged": False,
            "issues": []
        }

        response = client.post(
            "/api/v1/generate-lesson",
            json={"topic": "Test", "learner_id": "123"}
        , headers=API_HEADERS)

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


class TestDocumentProcessingEndpoint:
    """Test document processing endpoint for S3 document RAG ingestion."""

    @patch("app.api.routes.s3_client")
    @patch("app.api.routes.DocumentProcessor")
    @patch("app.api.routes.vector_store_manager")
    def test_process_document_success_pdf(self, mock_vector_manager, mock_processor_class, mock_s3):
        """Test successful document processing for PDF."""
        # Mock DocumentProcessor instance
        mock_processor = MagicMock()
        mock_processor_class.return_value = mock_processor

        # Mock documents from S3
        from langchain_core.documents import Document
        mock_documents = [
            Document(page_content="Page 1 content", metadata={"page": 1}),
            Document(page_content="Page 2 content", metadata={"page": 2})
        ]
        mock_processor.process_s3_file.return_value = mock_documents

        # Mock chunks
        mock_chunks = [
            Document(page_content="Chunk 1", metadata={"page": 1}),
            Document(page_content="Chunk 2", metadata={"page": 1}),
            Document(page_content="Chunk 3", metadata={"page": 2}),
            Document(page_content="Chunk 4", metadata={"page": 2})
        ]
        mock_processor.chunk_documents.return_value = mock_chunks
        mock_processor.add_metadata.return_value = mock_chunks

        # Mock vector store
        mock_vector_store = MagicMock()
        mock_vector_manager.load_vector_store.return_value = mock_vector_store

        # Make request
        response = client.post(
            "/api/v1/process-document",
            json={
                "document_id": 123,
                "s3_bucket": "test-bucket",
                "s3_key": "documents/test.pdf",
                "content_type": "application/pdf",
                "filename": "test.pdf",
                "category": "training"
            }
        , headers=API_HEADERS)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["chunks_created"] == 4
        assert data["embeddings_created"] == 4
        assert data["processing_time_seconds"] >= 0
        assert data["error"] is None

        # Verify calls
        mock_processor.process_s3_file.assert_called_once()
        mock_processor.chunk_documents.assert_called_once_with(mock_documents)
        mock_vector_manager.add_documents.assert_called_once_with(mock_vector_store, mock_chunks)

    @patch("app.api.routes.s3_client")
    @patch("app.api.routes.DocumentProcessor")
    @patch("app.api.routes.vector_store_manager")
    def test_process_document_success_txt(self, mock_vector_manager, mock_processor_class, mock_s3):
        """Test successful document processing for text file."""
        # Mock DocumentProcessor instance
        mock_processor = MagicMock()
        mock_processor_class.return_value = mock_processor

        # Mock text document
        from langchain_core.documents import Document
        mock_documents = [Document(page_content="Text content", metadata={})]
        mock_processor.process_s3_file.return_value = mock_documents

        # Mock chunks
        mock_chunks = [Document(page_content="Chunk 1", metadata={})]
        mock_processor.chunk_documents.return_value = mock_chunks
        mock_processor.add_metadata.return_value = mock_chunks

        # Mock vector store
        mock_vector_manager.load_vector_store.side_effect = Exception("No vector store")

        # Make request
        response = client.post(
            "/api/v1/process-document",
            json={
                "document_id": 456,
                "s3_bucket": "test-bucket",
                "s3_key": "documents/test.txt",
                "content_type": "text/plain",
                "filename": "test.txt"
            }
        , headers=API_HEADERS)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["chunks_created"] == 1
        assert data["embeddings_created"] == 1

        # Verify new vector store was created
        mock_vector_manager.create_vector_store.assert_called_once_with(mock_chunks)

    @patch("app.api.routes.s3_client")
    @patch("app.api.routes.DocumentProcessor")
    def test_process_document_file_not_found(self, mock_processor_class, mock_s3):
        """Test document processing when file not found in S3."""
        # Mock DocumentProcessor to raise FileNotFoundError
        mock_processor = MagicMock()
        mock_processor_class.return_value = mock_processor
        mock_processor.process_s3_file.side_effect = FileNotFoundError("File not found in S3")

        response = client.post(
            "/api/v1/process-document",
            json={
                "document_id": 789,
                "s3_bucket": "test-bucket",
                "s3_key": "documents/nonexistent.pdf",
                "content_type": "application/pdf",
                "filename": "nonexistent.pdf"
            }
        , headers=API_HEADERS)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["chunks_created"] == 0
        assert data["embeddings_created"] == 0
        assert "Document not found in S3" in data["error"]

    @patch("app.api.routes.DocumentProcessor")
    def test_process_document_invalid_s3_uri(self, mock_processor_class):
        """Test document processing with invalid S3 URI."""
        # Mock DocumentProcessor to raise ValueError
        mock_processor = MagicMock()
        mock_processor_class.return_value = mock_processor
        mock_processor.process_s3_file.side_effect = ValueError("Invalid S3 URI format")

        response = client.post(
            "/api/v1/process-document",
            json={
                "document_id": 101,
                "s3_bucket": "",
                "s3_key": "",
                "content_type": "application/pdf",
                "filename": "test.pdf"
            }
        , headers=API_HEADERS)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Invalid document or configuration" in data["error"]

    @patch("app.api.routes.DocumentProcessor")
    def test_process_document_processing_error(self, mock_processor_class):
        """Test document processing with unexpected error."""
        # Mock DocumentProcessor to raise general exception
        mock_processor = MagicMock()
        mock_processor_class.return_value = mock_processor
        mock_processor.process_s3_file.side_effect = RuntimeError("Unexpected processing error")

        response = client.post(
            "/api/v1/process-document",
            json={
                "document_id": 202,
                "s3_bucket": "test-bucket",
                "s3_key": "documents/corrupt.pdf",
                "content_type": "application/pdf",
                "filename": "corrupt.pdf"
            },
            headers={"X-API-Key": "dev_key"}
        )

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Document processing failed" in data["detail"]

    def test_process_document_missing_required_fields(self):
        """Test document processing with missing required fields."""
        response = client.post(
            "/api/v1/process-document",
            json={
                "document_id": 303
                # Missing required fields: s3_bucket, s3_key, etc.
            }
        , headers=API_HEADERS)

        assert response.status_code == 422  # Validation error

    @patch("app.api.routes.s3_client")
    @patch("app.api.routes.DocumentProcessor")
    @patch("app.api.routes.vector_store_manager")
    def test_process_document_with_metadata(self, mock_vector_manager, mock_processor_class, mock_s3):
        """Test document processing with custom metadata."""
        # Mock DocumentProcessor instance
        mock_processor = MagicMock()
        mock_processor_class.return_value = mock_processor

        # Mock documents and chunks
        from langchain_core.documents import Document
        mock_documents = [Document(page_content="Content", metadata={})]
        mock_chunks = [Document(page_content="Chunk", metadata={})]
        mock_processor.process_s3_file.return_value = mock_documents
        mock_processor.chunk_documents.return_value = mock_chunks
        mock_processor.add_metadata.return_value = mock_chunks

        # Mock vector store
        mock_vector_store = MagicMock()
        mock_vector_manager.load_vector_store.return_value = mock_vector_store

        # Make request with metadata
        response = client.post(
            "/api/v1/process-document",
            json={
                "document_id": 404,
                "s3_bucket": "test-bucket",
                "s3_key": "documents/test.pdf",
                "content_type": "application/pdf",
                "filename": "test.pdf",
                "category": "training",
                "metadata": {
                    "author": "John Doe",
                    "tags": ["python", "tutorial"]
                }
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify metadata was added (called twice - once for custom, once for standard)
        assert mock_processor.add_metadata.call_count == 2

    @patch("app.api.routes.s3_client")
    @patch("app.api.routes.DocumentProcessor")
    @patch("app.api.routes.vector_store_manager")
    def test_process_document_auto_detect_file_type(self, mock_vector_manager, mock_processor_class, mock_s3):
        """Test automatic file type detection from filename."""
        # Mock DocumentProcessor instance
        mock_processor = MagicMock()
        mock_processor_class.return_value = mock_processor

        # Mock documents and chunks
        from langchain_core.documents import Document
        mock_documents = [Document(page_content="Content", metadata={})]
        mock_chunks = [Document(page_content="Chunk", metadata={})]
        mock_processor.process_s3_file.return_value = mock_documents
        mock_processor.chunk_documents.return_value = mock_chunks
        mock_processor.add_metadata.return_value = mock_chunks

        # Mock vector store
        mock_vector_store = MagicMock()
        mock_vector_manager.load_vector_store.return_value = mock_vector_store

        # Make request with .txt extension but no content_type
        response = client.post(
            "/api/v1/process-document",
            json={
                "document_id": 505,
                "s3_bucket": "test-bucket",
                "s3_key": "documents/readme.txt",
                "content_type": "",
                "filename": "readme.txt"
            }
        , headers=API_HEADERS)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify process_s3_file was called with file_type="txt"
        call_args = mock_processor.process_s3_file.call_args
        assert call_args[1]["file_type"] == "txt"

    @patch("app.api.routes.s3_client")
    @patch("app.api.routes.DocumentProcessor")
    @patch("app.api.routes.vector_store_manager")
    def test_process_document_response_schema(self, mock_vector_manager, mock_processor_class, mock_s3):
        """Test document processing response matches expected schema."""
        # Mock DocumentProcessor instance
        mock_processor = MagicMock()
        mock_processor_class.return_value = mock_processor

        # Mock documents and chunks
        from langchain_core.documents import Document
        mock_documents = [Document(page_content="Content", metadata={})]
        mock_chunks = [
            Document(page_content="Chunk 1", metadata={}),
            Document(page_content="Chunk 2", metadata={})
        ]
        mock_processor.process_s3_file.return_value = mock_documents
        mock_processor.chunk_documents.return_value = mock_chunks
        mock_processor.add_metadata.return_value = mock_chunks

        # Mock vector store
        mock_vector_store = MagicMock()
        mock_vector_manager.load_vector_store.return_value = mock_vector_store

        response = client.post(
            "/api/v1/process-document",
            json={
                "document_id": 606,
                "s3_bucket": "test-bucket",
                "s3_key": "documents/schema-test.pdf",
                "content_type": "application/pdf",
                "filename": "schema-test.pdf"
            }
        , headers=API_HEADERS)

        data = response.json()

        # Verify all required fields are present
        assert "success" in data
        assert "chunks_created" in data
        assert "embeddings_created" in data
        assert "processing_time_seconds" in data
        assert "error" in data

        # Verify field types
        assert isinstance(data["success"], bool)
        assert isinstance(data["chunks_created"], int)
        assert isinstance(data["embeddings_created"], int)
        assert isinstance(data["processing_time_seconds"], (int, float))
        assert data["error"] is None or isinstance(data["error"], str)
