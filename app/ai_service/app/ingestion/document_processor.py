"""Document processing for vector store ingestion."""
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from typing import List, Dict, Any, Optional
import structlog

from app.ingestion.s3_document_loader import (
    S3FileLoader,
    S3DirectoryLoader,
    S3URIParser,
    S3DocumentLoaderFactory
)
from app.storage.s3_client import S3Client

logger = structlog.get_logger()


class DocumentProcessor:
    """Loads and chunks documents for vector store ingestion."""

    # Supported file types
    supported_types = ["pdf", "txt", "text"]

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        Initialize document processor.

        Args:
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks for context preservation
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len,
        )

    def process_file(self, file_path: str, file_type: str = "pdf") -> List[Document]:
        """
        Process a single file.

        Args:
            file_path: Path to file
            file_type: Type of file ("pdf" or "txt")

        Returns:
            List of loaded documents

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file type is unsupported
        """
        from pathlib import Path

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        logger.info("Processing file", path=file_path, type=file_type)

        if file_type == "pdf":
            loader = PyPDFLoader(file_path)
        elif file_type in ("txt", "text"):
            loader = TextLoader(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        documents = loader.load()
        logger.info("File processed", path=file_path, document_count=len(documents))
        return documents

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

        Raises:
            FileNotFoundError: If directory doesn't exist
            ValueError: If file type is unsupported
        """
        from pathlib import Path

        path = Path(directory)

        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")

        # Load documents
        if file_type == "pdf":
            documents = self.load_pdfs(directory)
        elif file_type in ("txt", "text"):
            documents = self.load_text_files(directory)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        # Add metadata if provided
        if metadata:
            documents = self.add_metadata(documents, metadata)

        # Chunk documents
        chunks = self.chunk_documents(documents)

        return chunks

    # ===================================================
    # S3 Document Processing Methods
    # ===================================================

    def process_s3_file(
        self,
        s3_uri: str,
        file_type: str = "pdf",
        s3_client: Optional[S3Client] = None
    ) -> List[Document]:
        """
        Process a single file from S3.

        Args:
            s3_uri: S3 URI (e.g., s3://bucket/path/to/file.pdf)
            file_type: Type of file ("pdf" or "txt")
            s3_client: Optional S3Client instance

        Returns:
            List of loaded documents

        Raises:
            FileNotFoundError: If file doesn't exist in S3
            ValueError: If S3 URI is invalid or file type unsupported
        """
        logger.info("Processing S3 file", s3_uri=s3_uri, file_type=file_type)

        # Validate S3 URI
        if not S3URIParser.is_s3_uri(s3_uri):
            raise ValueError(f"Invalid S3 URI format: {s3_uri}")

        # Create S3 loader
        loader = S3FileLoader(
            s3_uri=s3_uri,
            file_type=file_type,
            s3_client=s3_client
        )

        # Load documents
        documents = loader.load()
        logger.info("S3 file processed", s3_uri=s3_uri, document_count=len(documents))

        return documents

    def process_s3_directory(
        self,
        s3_uri: str,
        file_type: str = "pdf",
        metadata: Optional[Dict[str, Any]] = None,
        s3_client: Optional[S3Client] = None,
        max_files: Optional[int] = None
    ) -> List[Document]:
        """
        Process all files from an S3 prefix (directory).

        Args:
            s3_uri: S3 URI to directory (e.g., s3://bucket/path/to/dir/)
            file_type: Type of files to process ("pdf" or "txt")
            metadata: Optional metadata to add to all documents
            s3_client: Optional S3Client instance
            max_files: Maximum number of files to process

        Returns:
            Processed and chunked documents

        Raises:
            ValueError: If S3 URI is invalid or file type unsupported
        """
        logger.info("Processing S3 directory", s3_uri=s3_uri, file_type=file_type)

        # Validate S3 URI
        if not S3URIParser.is_s3_uri(s3_uri):
            raise ValueError(f"Invalid S3 URI format: {s3_uri}")

        # Create S3 directory loader
        glob_pattern = f"**/*.{file_type}" if file_type else "**/*"

        loader = S3DirectoryLoader(
            s3_uri=s3_uri,
            glob=glob_pattern,
            file_type=file_type,
            s3_client=s3_client,
            max_files=max_files
        )

        # Load documents
        documents = loader.load()

        # Add metadata if provided
        if metadata:
            documents = self.add_metadata(documents, metadata)

        # Chunk documents
        chunks = self.chunk_documents(documents)

        logger.info(
            "S3 directory processed",
            s3_uri=s3_uri,
            document_count=len(documents),
            chunk_count=len(chunks)
        )

        return chunks

    def batch_process_s3_files(
        self,
        s3_uris: List[str],
        file_type: str = "pdf",
        s3_client: Optional[S3Client] = None
    ) -> Dict[str, Any]:
        """
        Process multiple S3 files in batch.

        Args:
            s3_uris: List of S3 URIs to process
            file_type: Type of files to process
            s3_client: Optional S3Client instance

        Returns:
            Dict with success/failure counts and all documents
        """
        logger.info("Batch processing S3 files", file_count=len(s3_uris))

        all_documents = []
        success_count = 0
        failed_count = 0
        errors = []

        for s3_uri in s3_uris:
            try:
                documents = self.process_s3_file(
                    s3_uri=s3_uri,
                    file_type=file_type,
                    s3_client=s3_client
                )
                all_documents.extend(documents)
                success_count += 1

                logger.info("S3 file processed successfully", s3_uri=s3_uri)

            except Exception as e:
                failed_count += 1
                error_msg = f"{s3_uri}: {str(e)}"
                errors.append(error_msg)

                logger.error(
                    "Failed to process S3 file",
                    s3_uri=s3_uri,
                    error=str(e)
                )

        logger.info(
            "Batch S3 processing complete",
            total=len(s3_uris),
            success=success_count,
            failed=failed_count
        )

        return {
            'success_count': success_count,
            'failed_count': failed_count,
            'total_count': len(s3_uris),
            'documents': all_documents,
            'errors': errors
        }

    def process_multiple_sources(
        self,
        sources: List[Dict[str, str]],
        s3_client: Optional[S3Client] = None
    ) -> Dict[str, Any]:
        """
        Process documents from multiple sources (filesystem and S3).

        Args:
            sources: List of source dicts with 'type' ('local' or 's3')
                     and 'path' or 'uri' keys
            s3_client: Optional S3Client instance

        Returns:
            Dict with success/failure counts and all documents

        Example:
            sources = [
                {'type': 'local', 'path': '/path/to/file.pdf'},
                {'type': 's3', 'uri': 's3://bucket/file.pdf'}
            ]
        """
        logger.info("Processing multiple sources", source_count=len(sources))

        all_documents = []
        success_count = 0
        failed_count = 0

        for source in sources:
            source_type = source.get('type')

            try:
                if source_type == 'local':
                    path = source['path']
                    documents = self.process_file(path)

                elif source_type == 's3':
                    s3_uri = source['uri']
                    documents = self.process_s3_file(s3_uri, s3_client=s3_client)

                else:
                    raise ValueError(f"Unsupported source type: {source_type}")

                all_documents.extend(documents)
                success_count += 1

            except Exception as e:
                failed_count += 1
                logger.error(
                    "Failed to process source",
                    source=source,
                    error=str(e)
                )

        logger.info(
            "Multiple source processing complete",
            total=len(sources),
            success=success_count,
            failed=failed_count
        )

        return {
            'success_count': success_count,
            'failed_count': failed_count,
            'documents': all_documents
        }
