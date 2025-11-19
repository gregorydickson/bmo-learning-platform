"""
S3 Document Loaders for LangChain integration.

Provides LangChain-compatible document loaders for S3 sources:
- S3FileLoader: Load a single file from S3
- S3DirectoryLoader: Load all files from an S3 prefix

These loaders integrate with the existing DocumentProcessor and support
both local filesystem and S3 sources transparently.

Usage:
    from app.ingestion.s3_document_loader import S3FileLoader

    # Load single file
    loader = S3FileLoader(s3_uri="s3://bucket/path/to/file.pdf")
    documents = loader.load()

    # Load directory
    from app.ingestion.s3_document_loader import S3DirectoryLoader
    loader = S3DirectoryLoader(
        s3_uri="s3://bucket/path/to/directory/",
        glob="**/*.pdf"
    )
    documents = loader.load()
"""

import io
import os
import re
import tempfile
from pathlib import Path
from typing import List, Optional, Iterator
from urllib.parse import urlparse

from langchain_core.documents import Document
from langchain_core.document_loaders import BaseLoader
import boto3
from botocore.exceptions import ClientError
import structlog

from app.storage.s3_client import S3Client

logger = structlog.get_logger(__name__)


class S3URIParser:
    """Parse and validate S3 URIs."""

    S3_URI_PATTERN = re.compile(r'^s3://([^/]+)/(.+)$')

    @classmethod
    def parse(cls, s3_uri: str) -> tuple[str, str]:
        """
        Parse S3 URI into bucket and key.

        Args:
            s3_uri: S3 URI in format s3://bucket/key

        Returns:
            Tuple of (bucket, key)

        Raises:
            ValueError: If URI format is invalid

        Example:
            >>> S3URIParser.parse("s3://my-bucket/path/to/file.pdf")
            ('my-bucket', 'path/to/file.pdf')
        """
        match = cls.S3_URI_PATTERN.match(s3_uri)
        if not match:
            raise ValueError(
                f"Invalid S3 URI format: {s3_uri}. "
                "Expected format: s3://bucket/key"
            )

        bucket = match.group(1)
        key = match.group(2)

        return bucket, key

    @classmethod
    def is_s3_uri(cls, uri: str) -> bool:
        """Check if a URI is an S3 URI."""
        return uri.startswith('s3://')


class S3FileLoader(BaseLoader):
    """
    Load a single document from S3.

    Supports PDF and text files. Downloads the file to a temporary location,
    then uses the appropriate LangChain loader.

    This loader is designed to be a drop-in replacement for local file loaders.
    """

    def __init__(
        self,
        s3_uri: str,
        file_type: Optional[str] = None,
        s3_client: Optional[S3Client] = None
    ):
        """
        Initialize S3 file loader.

        Args:
            s3_uri: S3 URI (e.g., s3://bucket/path/to/file.pdf)
            file_type: File type ('pdf' or 'txt'). If None, inferred from extension
            s3_client: Optional S3Client instance. If None, creates default client

        Raises:
            ValueError: If s3_uri is invalid
        """
        self.s3_uri = s3_uri
        self.bucket, self.key = S3URIParser.parse(s3_uri)

        # Infer file type from extension if not provided
        if file_type is None:
            ext = Path(self.key).suffix.lower()
            if ext == '.pdf':
                self.file_type = 'pdf'
            elif ext in ('.txt', '.text'):
                self.file_type = 'txt'
            else:
                raise ValueError(
                    f"Cannot infer file type from extension: {ext}. "
                    "Please specify file_type parameter."
                )
        else:
            self.file_type = file_type

        self.s3_client = s3_client or S3Client()

        logger.info(
            "S3FileLoader initialized",
            s3_uri=s3_uri,
            bucket=self.bucket,
            key=self.key,
            file_type=self.file_type
        )

    def load(self) -> List[Document]:
        """
        Load document from S3.

        Downloads file to temporary location, loads with appropriate loader,
        then cleans up temporary file.

        Returns:
            List of Document objects

        Raises:
            FileNotFoundError: If file doesn't exist in S3
            ClientError: If S3 access fails
        """
        # Download to temporary file
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=Path(self.key).suffix
        ) as tmp_file:
            tmp_path = tmp_file.name

        try:
            # Download from S3
            logger.info("Downloading file from S3", s3_uri=self.s3_uri, tmp_path=tmp_path)

            result = self.s3_client.download_file(
                bucket=self.bucket,
                key=self.key,
                file_path=tmp_path
            )

            if not result['success']:
                raise FileNotFoundError(f"Failed to download {self.s3_uri}")

            # Load with appropriate LangChain loader
            documents = self._load_from_local_file(tmp_path)

            # Update metadata to include S3 source
            for doc in documents:
                doc.metadata['source'] = self.s3_uri
                doc.metadata['s3_bucket'] = self.bucket
                doc.metadata['s3_key'] = self.key

            logger.info(
                "Document loaded from S3",
                s3_uri=self.s3_uri,
                document_count=len(documents)
            )

            return documents

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code in ('404', 'NoSuchKey'):
                raise FileNotFoundError(f"File not found in S3: {self.s3_uri}") from e
            raise

        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _load_from_local_file(self, file_path: str) -> List[Document]:
        """
        Load document from local file using appropriate LangChain loader.

        Args:
            file_path: Path to local file

        Returns:
            List of Document objects
        """
        if self.file_type == 'pdf':
            from langchain_community.document_loaders import PyPDFLoader
            loader = PyPDFLoader(file_path)
        elif self.file_type in ('txt', 'text'):
            from langchain_community.document_loaders import TextLoader
            loader = TextLoader(file_path)
        else:
            raise ValueError(f"Unsupported file type: {self.file_type}")

        return loader.load()

    def lazy_load(self) -> Iterator[Document]:
        """
        Lazy load documents (for compatibility with BaseLoader).

        Yields documents one at a time instead of loading all at once.
        """
        documents = self.load()
        for doc in documents:
            yield doc


class S3DirectoryLoader(BaseLoader):
    """
    Load multiple documents from an S3 prefix (directory).

    Lists all objects under a prefix and loads each one using S3FileLoader.
    Supports glob patterns for filtering files.
    """

    def __init__(
        self,
        s3_uri: str,
        glob: str = "**/*",
        file_type: Optional[str] = None,
        s3_client: Optional[S3Client] = None,
        max_files: Optional[int] = None
    ):
        """
        Initialize S3 directory loader.

        Args:
            s3_uri: S3 URI to directory (e.g., s3://bucket/path/to/dir/)
            glob: Glob pattern for filtering files (default: all files)
            file_type: File type filter ('pdf', 'txt', or None for auto-detect)
            s3_client: Optional S3Client instance
            max_files: Maximum number of files to load (None = unlimited)

        Raises:
            ValueError: If s3_uri is invalid
        """
        self.s3_uri = s3_uri.rstrip('/') + '/'  # Ensure trailing slash
        self.bucket, self.prefix = S3URIParser.parse(self.s3_uri)
        self.glob = glob
        self.file_type = file_type
        self.max_files = max_files
        self.s3_client = s3_client or S3Client()

        logger.info(
            "S3DirectoryLoader initialized",
            s3_uri=s3_uri,
            bucket=self.bucket,
            prefix=self.prefix,
            glob=glob
        )

    def load(self) -> List[Document]:
        """
        Load all documents from S3 prefix.

        Returns:
            List of all Document objects from matching files

        Raises:
            ClientError: If S3 access fails
        """
        # List files in S3 prefix
        result = self.s3_client.list_files(
            bucket=self.bucket,
            prefix=self.prefix
        )

        if not result['success']:
            raise RuntimeError(f"Failed to list files in {self.s3_uri}")

        files = result['files']

        # Filter by glob pattern
        if self.glob and self.glob != "**/*":
            from fnmatch import fnmatch
            files = [
                f for f in files
                if fnmatch(f['key'], self.glob.replace('**/', '*'))
            ]

        # Filter by file type if specified
        if self.file_type:
            ext = f".{self.file_type}" if not self.file_type.startswith('.') else self.file_type
            files = [f for f in files if f['key'].endswith(ext)]

        # Limit number of files
        if self.max_files:
            files = files[:self.max_files]

        logger.info(
            "Loading files from S3 directory",
            bucket=self.bucket,
            prefix=self.prefix,
            file_count=len(files)
        )

        # Load each file
        all_documents = []
        for file_info in files:
            s3_uri = f"s3://{self.bucket}/{file_info['key']}"

            try:
                loader = S3FileLoader(
                    s3_uri=s3_uri,
                    file_type=self.file_type,
                    s3_client=self.s3_client
                )
                documents = loader.load()
                all_documents.extend(documents)

                logger.info(
                    "File loaded from S3",
                    s3_uri=s3_uri,
                    document_count=len(documents)
                )

            except Exception as e:
                logger.error(
                    "Failed to load file from S3",
                    s3_uri=s3_uri,
                    error=str(e)
                )
                # Continue loading other files even if one fails

        logger.info(
            "S3 directory loading complete",
            total_documents=len(all_documents),
            total_files=len(files)
        )

        return all_documents

    def lazy_load(self) -> Iterator[Document]:
        """
        Lazy load documents from S3 directory.

        Yields documents one file at a time for memory efficiency.
        """
        # List files
        result = self.s3_client.list_files(
            bucket=self.bucket,
            prefix=self.prefix
        )

        files = result['files']

        # Apply filters (same as load())
        if self.glob and self.glob != "**/*":
            from fnmatch import fnmatch
            files = [
                f for f in files
                if fnmatch(f['key'], self.glob.replace('**/', '*'))
            ]

        if self.file_type:
            ext = f".{self.file_type}" if not self.file_type.startswith('.') else self.file_type
            files = [f for f in files if f['key'].endswith(ext)]

        if self.max_files:
            files = files[:self.max_files]

        # Yield documents from each file
        for file_info in files:
            s3_uri = f"s3://{self.bucket}/{file_info['key']}"

            try:
                loader = S3FileLoader(
                    s3_uri=s3_uri,
                    file_type=self.file_type,
                    s3_client=self.s3_client
                )

                for doc in loader.lazy_load():
                    yield doc

            except Exception as e:
                logger.error(
                    "Failed to load file from S3",
                    s3_uri=s3_uri,
                    error=str(e)
                )
                # Continue with next file


class S3DocumentLoaderFactory:
    """Factory for creating appropriate S3 document loaders."""

    @staticmethod
    def create_loader(
        s3_uri: str,
        file_type: Optional[str] = None,
        s3_client: Optional[S3Client] = None,
        **kwargs
    ) -> BaseLoader:
        """
        Create appropriate loader based on S3 URI.

        Args:
            s3_uri: S3 URI (file or directory)
            file_type: File type ('pdf', 'txt', or None)
            s3_client: Optional S3Client instance
            **kwargs: Additional arguments for specific loaders

        Returns:
            S3FileLoader or S3DirectoryLoader instance
        """
        # If URI ends with file extension, it's a file
        path = Path(s3_uri)
        if path.suffix:
            return S3FileLoader(
                s3_uri=s3_uri,
                file_type=file_type,
                s3_client=s3_client
            )
        else:
            # Directory
            return S3DirectoryLoader(
                s3_uri=s3_uri,
                file_type=file_type,
                s3_client=s3_client,
                **kwargs
            )
