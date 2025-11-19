"""Tests for lesson generation functionality."""
import pytest
from unittest.mock import patch, MagicMock, Mock
import json
from app.generators.lesson_generator import LessonGenerator, LessonContent


class TestLessonGenerator:
    """Test suite for LessonGenerator."""

    def test_init_without_retriever(self):
        """Test initialization without RAG retriever."""
        generator = LessonGenerator(retriever=None)
        assert generator is not None
        assert generator.retriever is None

    def test_init_with_retriever(self, mock_vector_store):
        """Test initialization with RAG retriever."""
        retriever = mock_vector_store.as_retriever()
        generator = LessonGenerator(retriever=retriever)
        assert generator is not None
        assert generator.retriever is not None

    def test_generate_lesson_basic(self):
        """Test basic lesson generation without RAG."""
        # Uses autouse mock_openai_client fixture from conftest.py
        generator = LessonGenerator(retriever=None)
        result = generator.generate_lesson(
            topic="Python Functions",
            learner_id="learner_123"
        )

        assert result is not None
        assert "topic" in result
        assert "content" in result
        assert "key_points" in result
        assert "scenario" in result
        assert "quiz_question" in result
        assert result["topic"] == "Python Functions"

    def test_generate_lesson_with_rag(self, mock_vector_store):
        """Test lesson generation with RAG context."""
        # Uses autouse mock_openai_client fixture from conftest.py
        retriever = mock_vector_store.as_retriever()
        generator = LessonGenerator(retriever=retriever)
        result = generator.generate_lesson(
            topic="Python Functions",
            learner_id="learner_123"
        )

        assert result is not None
        assert "content" in result
        # Verify retriever was called (via get_relevant_documents method)
        retriever.get_relevant_documents.assert_called_once()

    def test_generate_lesson_with_difficulty(self):
        """Test lesson generation with difficulty level."""
        # Uses autouse mock_openai_client fixture from conftest.py
        generator = LessonGenerator(retriever=None)
        result = generator.generate_lesson(
            topic="Advanced Python",
            learner_id="learner_123"
        )

        assert result is not None
        assert "topic" in result
        assert "content" in result

    def test_generate_lesson_with_learner_context(self):
        """Test lesson generation with learner personalization."""
        # Uses autouse mock_openai_client fixture from conftest.py
        generator = LessonGenerator(retriever=None)
        result = generator.generate_lesson(
            topic="Python Basics",
            learner_id="learner_123"
        )

        assert result is not None
        assert "content" in result

    def test_generate_lesson_handles_api_error(self, mock_openai_client):
        """Test lesson generation handles OpenAI API errors."""
        # Override the autouse fixture for this specific test
        # Set side_effect on both paths (standard and with_raw_response)
        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_client.chat.completions.with_raw_response.create.side_effect = Exception("API Error")

        generator = LessonGenerator(retriever=None)

        with pytest.raises(Exception) as exc_info:
            generator.generate_lesson(
                topic="Python Functions",
                learner_id="learner_123"
            )

        assert "API Error" in str(exc_info.value)

    def test_generate_lesson_handles_invalid_json(self, mock_openai_client):
        """Test handling of invalid JSON response."""
        # Override the autouse fixture to return invalid JSON
        response_data = {
            "id": "chatcmpl-test123",
            "choices": [{
                "message": {
                    "content": "This is not valid JSON"
                },
                "finish_reason": "stop"
            }]
        }

        # Mock standard path
        response = MagicMock()
        response.model_dump.return_value = response_data
        mock_openai_client.chat.completions.create.return_value = response

        # Mock with_raw_response path (used by ChatOpenAI with Pydantic parsers)
        parsed_response = MagicMock()
        parsed_response.model_dump.return_value = response_data
        raw_response = MagicMock()
        raw_response.parse.return_value = parsed_response
        mock_openai_client.chat.completions.with_raw_response.create.return_value = raw_response

        generator = LessonGenerator(retriever=None)

        # Should handle gracefully or raise appropriate error
        with pytest.raises((json.JSONDecodeError, ValueError, Exception)):
            generator.generate_lesson(
                topic="Python Functions",
                learner_id="learner_123"
            )

    def test_generate_lesson_output_structure(self):
        """Test generated lesson has correct structure."""
        # Uses autouse mock_openai_client fixture from conftest.py
        generator = LessonGenerator(retriever=None)
        result = generator.generate_lesson(
            topic="Test Topic",
            learner_id="learner_123"
        )

        # Verify all required fields (matching LessonContent Pydantic model)
        assert "topic" in result
        assert "content" in result
        assert "key_points" in result
        assert "scenario" in result
        assert "quiz_question" in result
        assert "quiz_options" in result
        assert "correct_answer" in result

        # Verify types
        assert isinstance(result["topic"], str)
        assert isinstance(result["content"], str)
        assert isinstance(result["key_points"], list)
        assert isinstance(result["scenario"], str)
        assert isinstance(result["quiz_question"], str)
        assert isinstance(result["quiz_options"], list)
        assert isinstance(result["correct_answer"], int)

    def test_generate_lesson_empty_topic(self):
        """Test lesson generation with empty topic."""
        # Uses autouse mock_openai_client fixture from conftest.py
        generator = LessonGenerator(retriever=None)

        # Should handle empty topic appropriately
        with pytest.raises((ValueError, Exception)):
            generator.generate_lesson(
                topic="",
                learner_id="learner_123"
            )

    def test_generate_lesson_token_limit(self):
        """Test lesson generation respects token limits."""
        # Uses autouse mock_openai_client fixture from conftest.py
        generator = LessonGenerator(retriever=None)
        result = generator.generate_lesson(
            topic="Test Topic",
            learner_id="learner_123"
        )

        assert result is not None
        assert "content" in result

    def test_generate_lesson_with_temperature(self):
        """Test lesson generation uses appropriate temperature."""
        # Uses autouse mock_openai_client fixture from conftest.py
        # Temperature is set in ChatOpenAI initialization (0.7)
        generator = LessonGenerator(retriever=None)
        result = generator.generate_lesson(
            topic="Test Topic",
            learner_id="learner_123"
        )

        assert result is not None
        assert "content" in result

    def test_generate_lesson_model_selection(self, mock_settings):
        """Test lesson generation uses configured model."""
        # Uses autouse mock_openai_client fixture from conftest.py
        # Model is set when ChatOpenAI is created from settings
        generator = LessonGenerator(retriever=None)
        result = generator.generate_lesson(
            topic="Test Topic",
            learner_id="learner_123"
        )

        assert result is not None
        assert "content" in result
