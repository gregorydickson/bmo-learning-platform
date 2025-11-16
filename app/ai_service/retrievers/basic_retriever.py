"""Basic RAG retriever implementation."""
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from typing import List
import structlog

logger = structlog.get_logger()


class BasicRAGRetriever(BaseRetriever):
    """Basic retrieval augmented generation retriever."""

    vector_store: object
    search_kwargs: dict = {"k": 4}

    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun | None = None
    ) -> List[Document]:
        """
        Retrieve relevant documents for a query.

        Args:
            query: Search query
            run_manager: Callback manager

        Returns:
            List of relevant documents
        """
        logger.info("Retrieving documents", query=query[:100])

        k = self.search_kwargs.get("k", 4)
        documents = self.vector_store.similarity_search(query, k=k)

        logger.info(
            "Documents retrieved",
            count=len(documents),
            query_preview=query[:50]
        )

        return documents
