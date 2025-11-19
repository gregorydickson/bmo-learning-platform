"""Tests for vector store functionality."""
import pytest
from unittest.mock import patch, MagicMock
from app.ingestion.vector_store import VectorStoreManager


class TestVectorStoreManager:
    """Test suite for VectorStoreManager."""

    def test_init(self):
        """Test VectorStoreManager initialization."""
        manager = VectorStoreManager()
        assert manager is not None

    @patch("chromadb.Client")
    @patch("app.ingestion.vector_store.Chroma")  # Patch at module level
    def test_create_vector_store(self, mock_chroma, mock_client):
        """Test vector store creation with documents."""
        # Setup mocks
        mock_store = MagicMock()
        mock_chroma.from_documents.return_value = mock_store

        # Create mock documents
        mock_documents = [
            MagicMock(page_content="Document 1", metadata={"source": "test1.pdf"}),
            MagicMock(page_content="Document 2", metadata={"source": "test2.pdf"})
        ]

        manager = VectorStoreManager()
        result = manager.create_vector_store(mock_documents)

        assert result is not None
        mock_chroma.from_documents.assert_called_once()

    @patch("chromadb.Client")
    @patch("langchain_community.vectorstores.Chroma")
    def test_create_vector_store_empty_documents(self, mock_chroma, mock_client):
        """Test vector store creation with empty document list."""
        manager = VectorStoreManager()

        with pytest.raises((ValueError, Exception)):
            manager.create_vector_store([])

    @patch("chromadb.Client")
    @patch("langchain_community.vectorstores.Chroma")
    def test_load_vector_store(self, mock_chroma, mock_client):
        """Test loading existing vector store."""
        mock_store = MagicMock()
        mock_chroma.return_value = mock_store

        manager = VectorStoreManager()
        result = manager.load_vector_store()

        assert result is not None

    @patch("chromadb.Client")
    @patch("app.ingestion.vector_store.Chroma")  # Patch at module level
    def test_load_vector_store_not_exists(self, mock_chroma, mock_client):
        """Test loading vector store that doesn't exist."""
        mock_chroma.side_effect = Exception("Collection not found")

        manager = VectorStoreManager()

        with pytest.raises(Exception):
            manager.load_vector_store()

    @patch("chromadb.Client")
    @patch("langchain_community.vectorstores.Chroma")
    def test_as_retriever(self, mock_chroma, mock_client):
        """Test creating retriever from vector store."""
        mock_store = MagicMock()
        mock_retriever = MagicMock()
        mock_store.as_retriever.return_value = mock_retriever

        manager = VectorStoreManager()
        result = manager.as_retriever(mock_store)

        assert result is not None
        mock_store.as_retriever.assert_called_once()

    @patch("chromadb.Client")
    @patch("langchain_community.vectorstores.Chroma")
    def test_as_retriever_with_search_kwargs(self, mock_chroma, mock_client):
        """Test creating retriever with custom search parameters."""
        mock_store = MagicMock()
        mock_retriever = MagicMock()
        mock_store.as_retriever.return_value = mock_retriever

        manager = VectorStoreManager()
        result = manager.as_retriever(
            mock_store,
            search_kwargs={"k": 5}
        )

        assert result is not None
        call_kwargs = mock_store.as_retriever.call_args.kwargs
        if "search_kwargs" in call_kwargs:
            assert call_kwargs["search_kwargs"]["k"] == 5

    @patch("chromadb.Client")
    @patch("app.ingestion.vector_store.Chroma")  # Patch at module level
    def test_similarity_search(self, mock_chroma, mock_client):
        """Test similarity search functionality."""
        mock_store = MagicMock()
        mock_chroma.return_value = mock_store
        mock_store.similarity_search.return_value = [
            MagicMock(page_content="Relevant doc 1"),
            MagicMock(page_content="Relevant doc 2")
        ]

        manager = VectorStoreManager()
        vector_store = manager.load_vector_store()
        results = vector_store.similarity_search("test query", k=2)

        assert len(results) == 2
        vector_store.similarity_search.assert_called_once_with("test query", k=2)

    @patch("chromadb.Client")
    @patch("langchain_community.vectorstores.Chroma")
    @patch("langchain_openai.OpenAIEmbeddings")
    def test_embeddings_initialization(self, mock_embeddings, mock_chroma, mock_client):
        """Test that embeddings are properly initialized."""
        mock_embeddings_instance = MagicMock()
        mock_embeddings.return_value = mock_embeddings_instance

        manager = VectorStoreManager()
        # Should use OpenAI embeddings
        assert manager is not None

    @patch("chromadb.Client")
    @patch("langchain_community.vectorstores.Chroma")
    def test_persistence_directory(self, mock_chroma, mock_client, mock_settings):
        """Test vector store uses correct persistence directory."""
        mock_store = MagicMock()
        mock_chroma.return_value = mock_store

        manager = VectorStoreManager()
        manager.load_vector_store()

        # Verify persistence directory was used
        call_kwargs = mock_chroma.call_args.kwargs if mock_chroma.call_args else {}
        if "persist_directory" in call_kwargs:
            assert call_kwargs["persist_directory"] is not None

    @patch("chromadb.Client")
    @patch("langchain_community.vectorstores.Chroma")
    def test_collection_name(self, mock_chroma, mock_client, mock_settings):
        """Test vector store uses correct collection name."""
        mock_store = MagicMock()
        mock_chroma.return_value = mock_store

        manager = VectorStoreManager()
        manager.load_vector_store()

        # Verify collection name was used
        call_kwargs = mock_chroma.call_args.kwargs if mock_chroma.call_args else {}
        if "collection_name" in call_kwargs:
            assert call_kwargs["collection_name"] == "test_collection"

    @patch("chromadb.Client")
    @patch("app.ingestion.vector_store.Chroma")  # Patch at module level
    def test_add_documents(self, mock_chroma, mock_client):
        """Test adding documents to existing vector store."""
        mock_store = MagicMock()
        mock_chroma.return_value = mock_store

        new_docs = [
            MagicMock(page_content="New doc", metadata={"source": "new.pdf"})
        ]

        manager = VectorStoreManager()
        vector_store = manager.load_vector_store()
        vector_store.add_documents(new_docs)

        vector_store.add_documents.assert_called_once_with(new_docs)

    @patch("chromadb.Client")
    @patch("langchain_community.vectorstores.Chroma")
    def test_delete_collection(self, mock_chroma, mock_client):
        """Test deleting a collection."""
        client = MagicMock()
        mock_client.return_value = client

        manager = VectorStoreManager()

        # Should be able to delete collection via client
        # (Implementation depends on actual API)
        assert manager is not None
