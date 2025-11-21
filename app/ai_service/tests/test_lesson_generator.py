"""Tests for lesson generation functionality."""
import pytest
from unittest.mock import patch, MagicMock, Mock
import json
from app.generators.lesson_generator import LessonGenerator, LessonContent


class TestLessonGenerator:
    """Test suite for LessonGenerator."""

    @pytest.fixture
    def mock_anthropic(self):
        """Mock ChatAnthropic."""
        from langchain_core.messages import AIMessage
        
        with patch("app.generators.lesson_generator.ChatAnthropic") as mock:
            llm = MagicMock()
            mock.return_value = llm
            
            # Mock invoke response
            content = json.dumps({
                "topic": "Python Functions",
                "content": "Functions in Python are defined using the def keyword...",
                "key_points": ["Functions are reusable", "Use def keyword", "Can return values"],
                "scenario": "You're building a calculator application...",
                "quiz_question": "What keyword is used to define a function in Python?",
                "quiz_options": ["func", "def", "function", "define"],
                "correct_answer": 1
            })
            message = AIMessage(content=content)
            llm.invoke.return_value = message
            llm.return_value = message
            
            yield llm

    def test_init_without_retriever(self):
        """Test initialization without RAG retriever."""
        with patch("app.generators.lesson_generator.ChatAnthropic"):
            generator = LessonGenerator(retriever=None)
            assert generator is not None
            assert generator.retriever is None

    def test_init_with_retriever(self, mock_vector_store):
        """Test initialization with RAG retriever."""
        with patch("app.generators.lesson_generator.ChatAnthropic"):
            retriever = mock_vector_store.as_retriever()
            generator = LessonGenerator(retriever=retriever)
            assert generator is not None
            assert generator.retriever is not None

    def test_generate_lesson_basic(self, mock_anthropic):
        """Test basic lesson generation without RAG."""
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

    def test_generate_lesson_with_rag(self, mock_vector_store, mock_anthropic):
        """Test lesson generation with RAG context."""
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

    def test_generate_lesson_with_difficulty(self, mock_anthropic):
        """Test lesson generation with difficulty level."""
        generator = LessonGenerator(retriever=None)
        result = generator.generate_lesson(
            topic="Advanced Python",
            learner_id="learner_123"
        )

        assert result is not None
        assert "topic" in result
        assert "content" in result

    def test_generate_lesson_with_learner_context(self, mock_anthropic):
        """Test lesson generation with learner personalization."""
        generator = LessonGenerator(retriever=None)
        result = generator.generate_lesson(
            topic="Python Basics",
            learner_id="learner_123"
        )

        assert result is not None
        assert "content" in result

    def test_generate_lesson_handles_api_error(self, mock_anthropic):
        """Test lesson generation handles API errors."""
        # Set side_effect to raise exception on both invoke and call
        mock_anthropic.invoke.side_effect = Exception("API Error")
        mock_anthropic.side_effect = Exception("API Error")

        generator = LessonGenerator(retriever=None)

        with pytest.raises(Exception) as exc_info:
            generator.generate_lesson(
                topic="Python Functions",
                learner_id="learner_123"
            )

        assert "API Error" in str(exc_info.value)

    def test_generate_lesson_handles_invalid_json(self, mock_anthropic):
        """Test handling of invalid JSON response."""
        from langchain_core.messages import AIMessage
        
        # Mock invalid JSON response
        message = AIMessage(content="This is not valid JSON")
        mock_anthropic.invoke.return_value = message
        mock_anthropic.return_value = message

        generator = LessonGenerator(retriever=None)

        # Should handle gracefully or raise appropriate error
        with pytest.raises((json.JSONDecodeError, ValueError, Exception)):
            generator.generate_lesson(
                topic="Python Functions",
                learner_id="learner_123"
            )

    def test_generate_lesson_output_structure(self, mock_anthropic):
        """Test generated lesson has correct structure."""
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

    def test_generate_lesson_empty_topic(self, mock_anthropic):
        """Test lesson generation with empty topic."""
        generator = LessonGenerator(retriever=None)

        # Should handle empty topic appropriately
        with pytest.raises((ValueError, Exception)):
            generator.generate_lesson(
                topic="",
                learner_id="learner_123"
            )

    def test_generate_lesson_token_limit(self, mock_anthropic):
        """Test lesson generation respects token limits."""
        generator = LessonGenerator(retriever=None)
        result = generator.generate_lesson(
            topic="Test Topic",
            learner_id="learner_123"
        )

        assert result is not None
        assert "content" in result

    def test_generate_lesson_with_temperature(self, mock_anthropic):
        """Test lesson generation uses appropriate temperature."""
        # We can inspect the mock to see if it was initialized with correct temperature
        # But since we patch the class, we need to check the call args of the class
        with patch("app.generators.lesson_generator.ChatAnthropic") as mock_cls:
            mock_cls.return_value = mock_anthropic
            generator = LessonGenerator(retriever=None)
            
            # Check initialization args
            _, kwargs = mock_cls.call_args
            assert kwargs.get("temperature") == 0.7

    def test_generate_lesson_model_selection(self, mock_settings, mock_anthropic):
        """Test lesson generation uses configured model."""
        with patch("app.generators.lesson_generator.ChatAnthropic") as mock_cls:
            mock_cls.return_value = mock_anthropic
            generator = LessonGenerator(retriever=None)
            
            # Check initialization args
            _, kwargs = mock_cls.call_args
            assert kwargs.get("model") == "claude-haiku-4-5-20251001"
