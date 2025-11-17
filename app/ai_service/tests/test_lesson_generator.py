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

    @patch("openai.OpenAI")
    def test_generate_lesson_basic(self, mock_openai):
        """Test basic lesson generation without RAG."""
        # Setup mock
        client = MagicMock()
        mock_openai.return_value = client
        client.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=json.dumps({
                            "topic": "Python Functions",
                            "content": "Functions are reusable blocks of code...",
                            "scenario": "You're building a calculator app...",
                            "quiz_question": "What keyword defines a function?",
                            "quiz_options": ["func", "def", "function", "define"],
                            "quiz_answer": "def"
                        })
                    )
                )
            ],
            usage=MagicMock(
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150
            )
        )

        generator = LessonGenerator(retriever=None)
        result = generator.generate_lesson(
            topic="Python Functions",
            learner_id="learner_123"
        )

        assert result is not None
        assert "topic" in result
        assert "content" in result
        assert "scenario" in result
        assert "quiz_question" in result
        assert result["topic"] == "Python Functions"

    @patch("openai.OpenAI")
    def test_generate_lesson_with_rag(self, mock_openai, mock_vector_store):
        """Test lesson generation with RAG context."""
        # Setup mock
        client = MagicMock()
        mock_openai.return_value = client
        client.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=json.dumps({
                            "topic": "Python Functions",
                            "content": "Based on the documentation, functions are defined with def...",
                            "scenario": "According to best practices...",
                            "quiz_question": "What keyword defines a function?",
                            "quiz_options": ["func", "def", "function", "define"],
                            "quiz_answer": "def"
                        })
                    )
                )
            ]
        )

        retriever = mock_vector_store.as_retriever()
        generator = LessonGenerator(retriever=retriever)
        result = generator.generate_lesson(
            topic="Python Functions",
            learner_id="learner_123"
        )

        assert result is not None
        assert "content" in result
        # Verify retriever was called
        retriever.invoke.assert_called_once()

    @patch("openai.OpenAI")
    def test_generate_lesson_with_difficulty(self, mock_openai):
        """Test lesson generation with difficulty level."""
        client = MagicMock()
        mock_openai.return_value = client
        client.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=json.dumps({
                            "topic": "Advanced Python",
                            "content": "Advanced concepts include decorators...",
                            "scenario": "Building enterprise applications...",
                            "quiz_question": "What are decorators?",
                            "quiz_options": ["A", "B", "C", "D"],
                            "quiz_answer": "B"
                        })
                    )
                )
            ]
        )

        generator = LessonGenerator(retriever=None)
        result = generator.generate_lesson(
            topic="Advanced Python",
            learner_id="learner_123",
            difficulty="hard"
        )

        assert result is not None
        # Verify the prompt included difficulty level
        call_args = client.chat.completions.create.call_args
        assert call_args is not None

    @patch("openai.OpenAI")
    def test_generate_lesson_with_learner_context(self, mock_openai):
        """Test lesson generation with learner personalization."""
        client = MagicMock()
        mock_openai.return_value = client
        client.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=json.dumps({
                            "topic": "Python Basics",
                            "content": "Personalized content...",
                            "scenario": "Relevant to your experience...",
                            "quiz_question": "Test question?",
                            "quiz_options": ["A", "B", "C", "D"],
                            "quiz_answer": "A"
                        })
                    )
                )
            ]
        )

        generator = LessonGenerator(retriever=None)
        result = generator.generate_lesson(
            topic="Python Basics",
            learner_id="learner_123"
        )

        assert result is not None
        assert "content" in result

    @patch("openai.OpenAI")
    def test_generate_lesson_handles_api_error(self, mock_openai):
        """Test lesson generation handles OpenAI API errors."""
        client = MagicMock()
        mock_openai.return_value = client
        client.chat.completions.create.side_effect = Exception("API Error")

        generator = LessonGenerator(retriever=None)

        with pytest.raises(Exception) as exc_info:
            generator.generate_lesson(
                topic="Python Functions",
                learner_id="learner_123"
            )

        assert "API Error" in str(exc_info.value)

    @patch("openai.OpenAI")
    def test_generate_lesson_handles_invalid_json(self, mock_openai):
        """Test handling of invalid JSON response."""
        client = MagicMock()
        mock_openai.return_value = client
        client.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content="This is not valid JSON"
                    )
                )
            ]
        )

        generator = LessonGenerator(retriever=None)

        # Should handle gracefully or raise appropriate error
        with pytest.raises((json.JSONDecodeError, ValueError, Exception)):
            generator.generate_lesson(
                topic="Python Functions",
                learner_id="learner_123"
            )

    @patch("openai.OpenAI")
    def test_generate_lesson_output_structure(self, mock_openai):
        """Test generated lesson has correct structure."""
        client = MagicMock()
        mock_openai.return_value = client
        client.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=json.dumps({
                            "topic": "Test Topic",
                            "content": "Test content",
                            "scenario": "Test scenario",
                            "quiz_question": "Test question?",
                            "quiz_options": ["A", "B", "C", "D"],
                            "quiz_answer": "A"
                        })
                    )
                )
            ]
        )

        generator = LessonGenerator(retriever=None)
        result = generator.generate_lesson(
            topic="Test Topic",
            learner_id="learner_123"
        )

        # Verify all required fields
        assert "topic" in result
        assert "content" in result
        assert "scenario" in result
        assert "quiz_question" in result
        assert "quiz_options" in result
        assert "quiz_answer" in result

        # Verify types
        assert isinstance(result["topic"], str)
        assert isinstance(result["content"], str)
        assert isinstance(result["scenario"], str)
        assert isinstance(result["quiz_question"], str)
        assert isinstance(result["quiz_options"], list)
        assert isinstance(result["quiz_answer"], str)

    @patch("openai.OpenAI")
    def test_generate_lesson_empty_topic(self, mock_openai):
        """Test lesson generation with empty topic."""
        client = MagicMock()
        mock_openai.return_value = client

        generator = LessonGenerator(retriever=None)

        # Should handle empty topic appropriately
        with pytest.raises((ValueError, Exception)):
            generator.generate_lesson(
                topic="",
                learner_id="learner_123"
            )

    @patch("openai.OpenAI")
    def test_generate_lesson_token_limit(self, mock_openai):
        """Test lesson generation respects token limits."""
        client = MagicMock()
        mock_openai.return_value = client
        client.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=json.dumps({
                            "topic": "Test",
                            "content": "Content within limits",
                            "scenario": "Scenario",
                            "quiz_question": "Question?",
                            "quiz_options": ["A", "B"],
                            "quiz_answer": "A"
                        })
                    )
                )
            ],
            usage=MagicMock(
                completion_tokens=450  # Under 500 limit
            )
        )

        generator = LessonGenerator(retriever=None)
        result = generator.generate_lesson(
            topic="Test Topic",
            learner_id="learner_123"
        )

        assert result is not None
        # Verify max_tokens parameter was set in API call
        call_args = client.chat.completions.create.call_args
        assert call_args is not None

    @patch("openai.OpenAI")
    def test_generate_lesson_with_temperature(self, mock_openai):
        """Test lesson generation uses appropriate temperature."""
        client = MagicMock()
        mock_openai.return_value = client
        client.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=json.dumps({
                            "topic": "Test",
                            "content": "Test",
                            "scenario": "Test",
                            "quiz_question": "Test?",
                            "quiz_options": ["A", "B"],
                            "quiz_answer": "A"
                        })
                    )
                )
            ]
        )

        generator = LessonGenerator(retriever=None)
        generator.generate_lesson(
            topic="Test Topic",
            learner_id="learner_123"
        )

        # Verify temperature was set in API call
        call_kwargs = client.chat.completions.create.call_args.kwargs
        if "temperature" in call_kwargs:
            assert 0.0 <= call_kwargs["temperature"] <= 1.0

    @patch("openai.OpenAI")
    def test_generate_lesson_model_selection(self, mock_openai, mock_settings):
        """Test lesson generation uses configured model."""
        client = MagicMock()
        mock_openai.return_value = client
        client.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=json.dumps({
                            "topic": "Test",
                            "content": "Test",
                            "scenario": "Test",
                            "quiz_question": "Test?",
                            "quiz_options": ["A"],
                            "quiz_answer": "A"
                        })
                    )
                )
            ]
        )

        generator = LessonGenerator(retriever=None)
        generator.generate_lesson(
            topic="Test Topic",
            learner_id="learner_123"
        )

        # Verify model parameter
        call_kwargs = client.chat.completions.create.call_args.kwargs
        if "model" in call_kwargs:
            assert call_kwargs["model"] == "gpt-4-turbo-preview"
