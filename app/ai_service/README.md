# BMO Learning AI Service

LangChain-powered AI service for the BMO microlearning platform.

## Features

- Document ingestion and vector storage
- RAG (Retrieval Augmented Generation)
- Adaptive learning agents
- Content generation chains
- LLM safety guardrails

## Setup

### Prerequisites

- Python 3.11+
- uv (Python package manager)

### Installation

```bash
# Install dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Start development server
uv run uvicorn app.main:app --reload
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
app/ai_service/
├── app/
│   └── main.py           # FastAPI application
├── agents/               # LangChain agents
├── chains/              # LangChain chains
├── generators/          # Content generation
├── ingestion/           # Document loading
├── retrievers/          # RAG retrievers
├── safety/              # LLM safety layer
├── config/              # Configuration
└── tests/               # Test suite
```

## Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific test
uv run pytest tests/unit/test_example.py
```

## Development

See the main project README and Phase 2 workplan for implementation details.
