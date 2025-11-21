"""Pytest configuration and fixtures for AI service tests."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Generator
import tempfile
import os
import json
from dotenv import load_dotenv

# CRITICAL: Clear any production environment variables before loading test env
# This prevents leaking real AWS credentials, API keys, etc. into tests
_sensitive_vars = [
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "OPENAI_API_KEY",
    "LANGCHAIN_API_KEY",
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "SLACK_BOT_TOKEN",
]

for var in _sensitive_vars:
    os.environ.pop(var, None)

# Load test environment variables (must happen before any app imports)
load_dotenv(".env.test", override=True)


@pytest.fixture(autouse=True)
def mock_openai_client():
    """Mock OpenAI client for testing (auto-use for all tests)."""
    # Patch both at the source and at import locations for comprehensive coverage
    with patch("openai.OpenAI") as mock_class, \
         patch("app.safety.safety_validator.OpenAI", mock_class):
        client = MagicMock()
        mock_class.return_value = client

        # Create proper response structure that ChatOpenAI expects
        # CRITICAL: response.model_dump() must return a dict, not a MagicMock
        response_data = {
            "id": "chatcmpl-test123",
            "object": "chat.completion",
            "created": 1677652288,
            "model": "gpt-4-turbo-preview",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": json.dumps({
                        "topic": "Python Functions",
                        "content": "Functions in Python are defined using the def keyword...",
                        "key_points": ["Functions are reusable", "Use def keyword", "Can return values"],
                        "scenario": "You're building a calculator application...",
                        "quiz_question": "What keyword is used to define a function in Python?",
                        "quiz_options": ["func", "def", "function", "define"],
                        "correct_answer": 1
                    })
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }

        # Mock for standard path: client.chat.completions.create()
        response = MagicMock()
        response.model_dump.return_value = response_data
        client.chat.completions.create.return_value = response

        # Mock for structured output path: client.chat.completions.with_raw_response.create().parse()
        # This is used by ChatOpenAI with Pydantic output parsers
        parsed_response = MagicMock()
        parsed_response.model_dump.return_value = response_data

        raw_response = MagicMock()
        raw_response.parse.return_value = parsed_response

        with_raw = MagicMock()
        with_raw.create.return_value = raw_response

        client.chat.completions.with_raw_response = with_raw

        # Mock embeddings
        client.embeddings.create.return_value = MagicMock(
            data=[
                MagicMock(embedding=[0.1] * 1536)
            ]
        )

        # Mock moderation - default to clean
        moderation_result = MagicMock()
        moderation_result.flagged = False
        moderation_result.categories = MagicMock()
        moderation_result.categories.model_dump.return_value = {
            "hate": False,
            "violence": False,
            "sexual": False,
            "self_harm": False,
            "hate/threatening": False,
            "violence/graphic": False
        }
        client.moderations.create.return_value = MagicMock(
            results=[moderation_result]
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
    """Sample lesson generation response (matches LessonContent Pydantic model)."""
    return {
        "topic": "Python functions",
        "content": "Functions in Python are defined using the def keyword...",
        "key_points": [
            "Functions are reusable blocks of code",
            "Defined with the def keyword",
            "Can accept parameters and return values"
        ],
        "scenario": "You're building a calculator application...",
        "quiz_question": "What keyword is used to define a function in Python?",
        "quiz_options": ["func", "def", "function", "define"],
        "correct_answer": 1  # Index of correct answer (0-3)
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
    """Mock application settings with environment isolation."""
    # Clear get_settings cache
    from app.config.settings import get_settings
    get_settings.cache_clear()

    with patch("app.config.settings.settings") as mock:
        mock.openai_api_key = "sk-test-key"
        mock.anthropic_api_key = "sk-ant-test-key"
        mock.anthropic_model = "claude-haiku-4-5-20251001"
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
        mock.langchain_tracing_v2 = False
        mock.langchain_api_key = None
        mock.aws_access_key_id = None
        mock.aws_secret_access_key = None
        mock.aws_region = "us-east-2"  # Matches production terraform region
        mock.twilio_account_sid = None
        mock.twilio_auth_token = None
        mock.slack_bot_token = None
        mock.allowed_origins = ["http://localhost:3000", "http://localhost:3001"]
        yield mock

    # Clear cache again after test
    get_settings.cache_clear()


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
    """Reset environment variables between tests with security safeguards."""
    # Save original but remove sensitive production values
    original_env = os.environ.copy()

    yield

    # Restore environment but strip sensitive production values
    os.environ.clear()
    for key, value in original_env.items():
        # Don't restore production credentials - always use test values
        if key not in _sensitive_vars:
            os.environ[key] = value

    # ONLY set REQUIRED test values (not optional ones like AWS credentials)
    # This allows tests to verify default values and optional field behavior
    required_test_defaults = {
        "OPENAI_API_KEY": "sk-test-key-for-testing-only",
        "ANTHROPIC_API_KEY": "sk-ant-test-key-for-testing-only",
        "DATABASE_URL": "postgresql://localhost:5432/test_db",
        "REDIS_URL": "redis://localhost:6379/0",
    }

    for key, value in required_test_defaults.items():
        if key not in os.environ:
            os.environ[key] = value


# ChatOpenAI mock removed - we mock at OpenAI client level instead
# This allows LangChain's ChatOpenAI to use its real code path with our mocked OpenAI client


@pytest.fixture(autouse=True)
def mock_langchain_embeddings():
    """Mock LangChain OpenAI embeddings."""
    with patch("langchain_openai.OpenAIEmbeddings") as mock:
        embeddings = MagicMock()
        mock.return_value = embeddings

        # Mock embed_query
        embeddings.embed_query.return_value = [0.1] * 1536

        # Mock embed_documents
        embeddings.embed_documents.return_value = [[0.1] * 1536]

        yield embeddings


# ChatPromptTemplate and JsonOutputParser mocks removed
# LangChain's real implementation will work correctly with mocked OpenAI client
# The OpenAI client mock returns properly formatted JSON that the parser can handle


@pytest.fixture
def mock_document_loaders():
    """Mock LangChain document loaders."""
    with patch("langchain_community.document_loaders.PyPDFLoader") as pdf_mock, \
         patch("langchain_community.document_loaders.TextLoader") as text_mock, \
         patch("langchain_community.document_loaders.DirectoryLoader") as dir_mock:

        # Mock PDF loader
        pdf_loader = MagicMock()
        pdf_mock.return_value = pdf_loader
        pdf_loader.load.return_value = [
            MagicMock(
                page_content="Sample PDF content",
                metadata={"source": "test.pdf", "page": 1}
            )
        ]

        # Mock text loader
        text_loader = MagicMock()
        text_mock.return_value = text_loader
        text_loader.load.return_value = [
            MagicMock(
                page_content="Sample text content",
                metadata={"source": "test.txt"}
            )
        ]

        # Mock directory loader
        dir_loader = MagicMock()
        dir_mock.return_value = dir_loader
        dir_loader.load.return_value = [
            MagicMock(
                page_content="Document 1 content",
                metadata={"source": "doc1.pdf"}
            ),
            MagicMock(
                page_content="Document 2 content",
                metadata={"source": "doc2.pdf"}
            )
        ]

        yield {
            "pdf": pdf_loader,
            "text": text_loader,
            "directory": dir_loader
        }


@pytest.fixture
def mock_text_splitter():
    """Mock RecursiveCharacterTextSplitter."""
    with patch("langchain_text_splitters.RecursiveCharacterTextSplitter") as mock:
        splitter = MagicMock()
        mock.return_value = splitter

        # Mock split_documents
        splitter.split_documents.return_value = [
            MagicMock(
                page_content="Chunk 1 content",
                metadata={"chunk": 0, "source": "test.pdf"}
            ),
            MagicMock(
                page_content="Chunk 2 content",
                metadata={"chunk": 1, "source": "test.pdf"}
            )
        ]

        yield splitter


@pytest.fixture(autouse=True)
def mock_chroma_enhanced():
    """Enhanced mock for Chroma vector store."""
    with patch("langchain_community.vectorstores.Chroma") as mock:
        # Create vector store instance
        store = MagicMock()

        # Mock constructor
        mock.return_value = store

        # Mock from_documents class method
        mock.from_documents.return_value = store

        # Mock similarity_search
        store.similarity_search.return_value = [
            MagicMock(
                page_content="Relevant document 1",
                metadata={"source": "doc1.pdf", "relevance": 0.9}
            ),
            MagicMock(
                page_content="Relevant document 2",
                metadata={"source": "doc2.pdf", "relevance": 0.8}
            )
        ]

        # Mock similarity_search_with_score
        store.similarity_search_with_score.return_value = [
            (MagicMock(page_content="Doc 1", metadata={"source": "doc1.pdf"}), 0.9),
            (MagicMock(page_content="Doc 2", metadata={"source": "doc2.pdf"}), 0.8)
        ]

        # Mock add_documents
        store.add_documents.return_value = ["id1", "id2", "id3"]

        # Mock as_retriever
        retriever = MagicMock()
        store.as_retriever.return_value = retriever

        # Mock retriever invoke (for LCEL chains)
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

        # Mock retriever get_relevant_documents (for older retriever interface)
        retriever.get_relevant_documents.return_value = [
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


# ===================================================
# AWS Credentials Mock (moto) for Unit Tests
# ===================================================

@pytest.fixture(scope="session", autouse=True)
def aws_credentials():
    """
    Mocked AWS credentials for moto testing.

    This is a session-scoped fixture that sets AWS environment variables
    to dummy values so that boto3 clients don't try to use real credentials.

    Auto-use means this applies to ALL tests (both unit and integration).
    Integration tests will override these with LocalStack-specific values.
    """
    import os

    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-2"


# ===================================================
# LocalStack / AWS Integration Test Fixtures
# ===================================================

@pytest.fixture(scope="session")
def localstack_endpoint_url():
    """LocalStack endpoint URL - configurable via environment."""
    return os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")


@pytest.fixture(scope="session")
def localstack_s3(localstack_endpoint_url):
    """
    Session-scoped boto3 S3 client for LocalStack integration tests.

    Only used for integration tests marked with @pytest.mark.integration
    Connects to LocalStack on localhost:4566 or AWS_ENDPOINT_URL.

    Skip if LocalStack not running (allows unit tests to pass in CI).
    """
    import boto3
    from botocore.exceptions import EndpointConnectionError

    client = boto3.client(
        's3',
        endpoint_url=localstack_endpoint_url,
        aws_access_key_id='test',
        aws_secret_access_key='test',
        region_name='us-east-2'
    )

    # Verify LocalStack is accessible
    try:
        client.list_buckets()
    except EndpointConnectionError:
        pytest.skip("LocalStack is not running - skipping integration tests")

    return client


@pytest.fixture(scope="function")
def s3_test_bucket(localstack_s3):
    """
    Function-scoped S3 test bucket for integration tests.

    Creates a unique bucket for each test, yields the name, then cleans up.
    Ensures complete test isolation - no state leakage between tests.
    """
    import uuid

    # Create unique bucket name for this test
    bucket_name = f"test-bucket-{uuid.uuid4().hex[:12]}"

    # Create bucket
    localstack_s3.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={'LocationConstraint': 'us-east-2'}
    )

    yield bucket_name

    # Cleanup: Delete all objects then bucket
    try:
        # List and delete all objects (including versions if versioning enabled)
        response = localstack_s3.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in response:
            objects = [{'Key': obj['Key']} for obj in response['Contents']]
            if objects:
                localstack_s3.delete_objects(
                    Bucket=bucket_name,
                    Delete={'Objects': objects}
                )

        # Delete bucket
        localstack_s3.delete_bucket(Bucket=bucket_name)
    except Exception as e:
        # Log but don't fail test cleanup
        print(f"Warning: Failed to cleanup bucket {bucket_name}: {e}")


@pytest.fixture
def s3_client(localstack_endpoint_url):
    """
    S3Client instance configured for LocalStack.

    This is the fixture that integration tests will use.
    Returns the actual S3Client class instance we're testing.
    """
    # Import here to avoid circular dependencies
    from app.storage.s3_client import S3Client

    # Override settings for LocalStack
    os.environ['AWS_ENDPOINT_URL'] = localstack_endpoint_url
    os.environ['AWS_ACCESS_KEY_ID'] = 'test'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
    os.environ['AWS_REGION'] = 'us-east-2'
    os.environ['USE_LOCALSTACK'] = 'true'

    return S3Client()


@pytest.fixture(scope="session")
def localstack_secretsmanager(localstack_endpoint_url):
    """
    Session-scoped boto3 Secrets Manager client for LocalStack integration tests.

    Used for testing secret retrieval and rotation.
    """
    import boto3
    from botocore.exceptions import EndpointConnectionError

    client = boto3.client(
        'secretsmanager',
        endpoint_url=localstack_endpoint_url,
        aws_access_key_id='test',
        aws_secret_access_key='test',
        region_name='us-east-2'
    )

    # Verify LocalStack is accessible
    try:
        client.list_secrets()
    except EndpointConnectionError:
        pytest.skip("LocalStack is not running - skipping integration tests")

    return client


@pytest.fixture
def test_secret(localstack_secretsmanager):
    """
    Function-scoped test secret in Secrets Manager.

    Creates a secret, yields its name, then cleans up.
    """
    import uuid
    import json

    secret_name = f"test-secret-{uuid.uuid4().hex[:12]}"
    secret_value = {
        "api_key": "sk-test-fake-api-key",
        "username": "testuser",
        "password": "testpass123"
    }

    # Create secret
    localstack_secretsmanager.create_secret(
        Name=secret_name,
        SecretString=json.dumps(secret_value)
    )

    yield secret_name, secret_value

    # Cleanup
    try:
        localstack_secretsmanager.delete_secret(
            SecretId=secret_name,
            ForceDeleteWithoutRecovery=True
        )
    except Exception as e:
        print(f"Warning: Failed to cleanup secret {secret_name}: {e}")


# ===================================================
# Pytest Configuration
# ===================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (require LocalStack)"
    )
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )


def pytest_collection_modifyitems(config, items):
    """
    Automatically skip integration tests if LocalStack not running.

    This allows unit tests to pass in environments where LocalStack isn't available.
    """
    if config.getoption("-m") == "not integration":
        # User explicitly excluded integration tests
        return

    # Check if LocalStack is accessible
    localstack_available = False
    try:
        import boto3
        from botocore.exceptions import EndpointConnectionError

        endpoint_url = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
        client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id='test',
            aws_secret_access_key='test',
            region_name='us-east-2'
        )
        client.list_buckets()
        localstack_available = True
    except (ImportError, EndpointConnectionError, Exception):
        localstack_available = False

    if not localstack_available:
        skip_integration = pytest.mark.skip(reason="LocalStack not running")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
