"""Document processing for vector store ingestion."""
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from typing import List
import structlog

logger = structlog.get_logger()


class DocumentProcessor:
    """Loads and chunks documents for vector store ingestion."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        Initialize document processor.

        Args:
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks for context preservation
        """
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len,
        )

    def load_pdfs(self, directory: str) -> List[Document]:
        """
        Load all PDFs from a directory.

        Args:
            directory: Path to directory containing PDFs

        Returns:
            List of loaded documents
        """
        logger.info("Loading PDFs", directory=directory)

        loader = DirectoryLoader(
            directory,
            glob="**/*.pdf",
            loader_cls=PyPDFLoader,
            show_progress=True,
        )

        documents = loader.load()
        logger.info("PDFs loaded", count=len(documents))
        return documents

    def load_text_files(self, directory: str) -> List[Document]:
        """
        Load all text files from a directory.

        Args:
            directory: Path to directory containing text files

        Returns:
            List of loaded documents
        """
        logger.info("Loading text files", directory=directory)

        loader = DirectoryLoader(
            directory,
            glob="**/*.txt",
            loader_cls=TextLoader,
            show_progress=True,
        )

        documents = loader.load()
        logger.info("Text files loaded", count=len(documents))
        return documents

    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into chunks.

        Args:
            documents: List of documents to chunk

        Returns:
            List of chunked documents
        """
        logger.info("Chunking documents", input_count=len(documents))

        chunks = self.splitter.split_documents(documents)

        logger.info(
            "Documents chunked",
            input_count=len(documents),
            output_count=len(chunks)
        )
        return chunks

    def add_metadata(
        self,
        documents: List[Document],
        metadata: dict
    ) -> List[Document]:
        """
        Add metadata to all documents.

        Args:
            documents: List of documents
            metadata: Metadata to add

        Returns:
            Documents with added metadata
        """
        for doc in documents:
            doc.metadata.update(metadata)

        logger.info("Metadata added", document_count=len(documents))
        return documents

    def process_directory(
        self,
        directory: str,
        file_type: str = "pdf",
        metadata: dict | None = None
    ) -> List[Document]:
        """
        Complete processing pipeline for a directory.

        Args:
            directory: Path to directory
            file_type: Type of files to process ("pdf" or "txt")
            metadata: Optional metadata to add to all documents

        Returns:
            Processed and chunked documents
        """
        # Load documents
        if file_type == "pdf":
            documents = self.load_pdfs(directory)
        elif file_type == "txt":
            documents = self.load_text_files(directory)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        # Add metadata if provided
        if metadata:
            documents = self.add_metadata(documents, metadata)

        # Chunk documents
        chunks = self.chunk_documents(documents)

        return chunks
