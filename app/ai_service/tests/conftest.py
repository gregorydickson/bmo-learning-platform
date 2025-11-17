"""Pytest configuration and fixtures for AI service tests."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Generator
import tempfile
import os


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    with patch("openai.OpenAI") as mock:
        client = MagicMock()
        mock.return_value = client

        # Mock chat completion
        client.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content='{"topic": "Test Topic", "content": "Test lesson content", "scenario": "Test scenario", "quiz_question": "What is 2+2?", "quiz_options": ["3", "4", "5"], "quiz_answer": "4"}'
                    )
                )
            ],
            usage=MagicMock(
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150
            )
        )

        # Mock embeddings
        client.embeddings.create.return_value = MagicMock(
            data=[
                MagicMock(embedding=[0.1] * 1536)
            ]
        )

        # Mock moderation
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

        yield client


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    with patch("redis.Redis") as mock:
        redis_client = MagicMock()
        mock.return_value = redis_client

        # Mock cache operations
        redis_client.get.return_value = None
        redis_client.set.return_value = True
        redis_client.delete.return_value = 1
        redis_client.exists.return_value = False

        yield redis_client


@pytest.fixture
def mock_chroma_client():
    """Mock Chroma vector store client."""
    with patch("chromadb.Client") as mock:
        client = MagicMock()
        mock.return_value = client

        # Mock collection
        collection = MagicMock()
        client.get_or_create_collection.return_value = collection
        client.get_collection.return_value = collection

        # Mock query results
        collection.query.return_value = {
            "ids": [["doc1", "doc2"]],
            "distances": [[0.1, 0.2]],
            "documents": [["Document 1 content", "Document 2 content"]],
            "metadatas": [[{"source": "test1.pdf"}, {"source": "test2.pdf"}]]
        }

        collection.add.return_value = None
        collection.count.return_value = 10

        yield client


@pytest.fixture
def temp_chroma_dir() -> Generator[str, None, None]:
    """Create temporary directory for Chroma persistence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_lesson_request():
    """Sample lesson generation request."""
    return {
        "topic": "Python functions",
        "learner_id": "learner_123",
        "difficulty": "medium"
    }


@pytest.fixture
def sample_lesson_response():
    """Sample lesson generation response."""
    return {
        "topic": "Python functions",
        "content": "Functions in Python are defined using the def keyword...",
        "scenario": "You're building a calculator application...",
        "quiz_question": "What keyword is used to define a function in Python?",
        "quiz_options": ["func", "def", "function", "define"],
        "quiz_answer": "def"
    }


@pytest.fixture
def sample_document_content():
    """Sample document content for testing."""
    return """
    # Python Functions Tutorial

    Functions are reusable blocks of code that perform specific tasks.
    They help organize code and make it more maintainable.

    ## Defining Functions
    Use the def keyword followed by the function name and parentheses.

    Example:
    def greet(name):
        return f"Hello, {name}!"
    """


@pytest.fixture
def sample_pdf_path(tmp_path):
    """Create a sample PDF file for testing."""
    pdf_path = tmp_path / "test_document.pdf"
    # Create a simple text file (in real tests, would use actual PDF)
    pdf_path.write_text("Sample PDF content about Python programming.")
    return str(pdf_path)


@pytest.fixture
def mock_settings():
    """Mock application settings."""
    with patch("app.config.settings.settings") as mock:
        mock.openai_api_key = "sk-test-key"
        mock.openai_model = "gpt-4-turbo-preview"
        mock.openai_embedding_model = "text-embedding-3-small"
        mock.database_url = "postgresql://localhost:5432/test_db"
        mock.redis_url = "redis://localhost:6379/0"
        mock.chroma_persist_directory = "/tmp/test_chroma"
        mock.vector_store_collection = "test_collection"
        mock.enable_constitutional_ai = True
        mock.enable_pii_detection = True
        mock.max_tokens_per_lesson = 500
        mock.enable_llm_cache = True
        mock.cache_ttl_seconds = 3600
        mock.rate_limit_per_minute = 60
        mock.python_env = "test"
        mock.log_level = "DEBUG"
        yield mock


@pytest.fixture
def pii_test_cases():
    """Test cases for PII detection."""
    return {
        "ssn": "My SSN is 123-45-6789",
        "credit_card": "Card number: 4532-1234-5678-9010",
        "email": "Contact me at john.doe@example.com",
        "phone": "Call me at (555) 123-4567",
        "clean": "This is clean content without PII"
    }


@pytest.fixture
def unsafe_content_cases():
    """Test cases for content moderation."""
    return {
        "violent": "This contains violent content",
        "hateful": "This contains hate speech",
        "clean": "This is safe educational content"
    }


@pytest.fixture
def mock_vector_store():
    """Mock vector store with retriever."""
    with patch("langchain_community.vectorstores.Chroma") as mock:
        store = MagicMock()
        mock.return_value = store

        # Mock as_retriever
        retriever = MagicMock()
        store.as_retriever.return_value = retriever

        # Mock invoke for retriever
        retriever.invoke.return_value = [
            MagicMock(
                page_content="Python functions are defined with def keyword",
                metadata={"source": "python_tutorial.pdf"}
            ),
            MagicMock(
                page_content="Functions can have parameters and return values",
                metadata={"source": "python_tutorial.pdf"}
            )
        ]

        yield store


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables between tests."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)
