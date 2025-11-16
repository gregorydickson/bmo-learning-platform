"""Vector store management using ChromaDB."""
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from typing import List
import structlog

from app.config.settings import settings

logger = structlog.get_logger()


class VectorStoreManager:
    """Manages vector store operations for document retrieval."""

    def __init__(self):
        """Initialize vector store manager."""
        self.embeddings = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            openai_api_key=settings.openai_api_key
        )
        self.persist_directory = settings.chroma_persist_directory
        self.collection_name = settings.vector_store_collection

    def create_vector_store(self, documents: List[Document]) -> Chroma:
        """
        Create a new vector store from documents.

        Args:
            documents: List of documents to index

        Returns:
            Chroma vector store instance
        """
        logger.info(
            "Creating vector store",
            document_count=len(documents),
            collection=self.collection_name
        )

        vector_store = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            collection_name=self.collection_name,
            persist_directory=self.persist_directory
        )

        logger.info("Vector store created", collection=self.collection_name)
        return vector_store

    def load_vector_store(self) -> Chroma:
        """
        Load existing vector store from disk.

        Returns:
            Chroma vector store instance
        """
        logger.info("Loading vector store", collection=self.collection_name)

        vector_store = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory
        )

        logger.info("Vector store loaded")
        return vector_store

    def add_documents(
        self,
        vector_store: Chroma,
        documents: List[Document]
    ) -> List[str]:
        """
        Add documents to existing vector store.

        Args:
            vector_store: Existing vector store
            documents: Documents to add

        Returns:
            List of document IDs
        """
        logger.info("Adding documents to vector store", count=len(documents))

        ids = vector_store.add_documents(documents)

        logger.info("Documents added", count=len(ids))
        return ids

    def similarity_search(
        self,
        vector_store: Chroma,
        query: str,
        k: int = 4
    ) -> List[Document]:
        """
        Perform similarity search.

        Args:
            vector_store: Vector store to search
            query: Search query
            k: Number of results to return

        Returns:
            List of relevant documents
        """
        logger.info("Performing similarity search", query=query[:50], k=k)

        results = vector_store.similarity_search(query, k=k)

        logger.info("Search completed", result_count=len(results))
        return results

    def similarity_search_with_score(
        self,
        vector_store: Chroma,
        query: str,
        k: int = 4
    ) -> List[tuple[Document, float]]:
        """
        Perform similarity search with relevance scores.

        Args:
            vector_store: Vector store to search
            query: Search query
            k: Number of results to return

        Returns:
            List of (document, score) tuples
        """
        logger.info("Performing similarity search with scores", query=query[:50])

        results = vector_store.similarity_search_with_score(query, k=k)

        logger.info(
            "Search with scores completed",
            result_count=len(results),
            top_score=results[0][1] if results else None
        )
        return results

    def as_retriever(
        self,
        vector_store: Chroma,
        search_kwargs: dict | None = None
    ):
        """
        Convert vector store to retriever interface.

        Args:
            vector_store: Vector store instance
            search_kwargs: Search parameters (e.g., {"k": 4})

        Returns:
            Retriever interface
        """
        if search_kwargs is None:
            search_kwargs = {"k": 4}

        return vector_store.as_retriever(search_kwargs=search_kwargs)
