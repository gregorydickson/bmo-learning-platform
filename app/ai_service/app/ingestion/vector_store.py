"""Vector store management using ChromaDB."""
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from typing import List, Dict, Any, Optional
import structlog
import tarfile
import shutil
import tempfile
from pathlib import Path

from app.config.settings import settings
from app.storage.s3_client import S3Client

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

        Raises:
            ValueError: If documents list is empty
        """
        if not documents:
            raise ValueError("Cannot create vector store with empty document list")

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

    # ===================================================
    # S3 Backup and Restore Methods
    # ===================================================

    def backup_to_s3(
        self,
        bucket: str,
        key: str,
        s3_client: Optional[S3Client] = None,
        incremental: bool = False
    ) -> Dict[str, Any]:
        """
        Backup vector store to S3.

        Creates a tar.gz archive of the Chroma persist directory
        and uploads it to S3.

        Args:
            bucket: S3 bucket name
            key: S3 object key (e.g., 'backups/vector-store.tar.gz')
            s3_client: Optional S3Client instance
            incremental: If True, only backup changes since last backup (future feature)

        Returns:
            Dict with success status and backup info

        Raises:
            FileNotFoundError: If persist directory doesn't exist
            S3ClientError: If S3 upload fails
        """
        client = s3_client or S3Client()

        persist_path = Path(self.persist_directory)

        if not persist_path.exists():
            raise FileNotFoundError(
                f"Vector store persist directory not found: {self.persist_directory}"
            )

        logger.info(
            "Starting vector store backup to S3",
            persist_directory=self.persist_directory,
            bucket=bucket,
            key=key,
            incremental=incremental
        )

        # Create temporary tar.gz archive
        with tempfile.TemporaryDirectory() as tmp_dir:
            archive_path = Path(tmp_dir) / "vector-store-backup.tar.gz"

            # Create tar.gz of persist directory
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(
                    self.persist_directory,
                    arcname=Path(self.persist_directory).name
                )

            # Get archive size
            backup_size = archive_path.stat().st_size

            logger.info(
                "Vector store archive created",
                archive_size=backup_size,
                archive_path=str(archive_path)
            )

            # Upload to S3
            result = client.upload_file(
                file_path=str(archive_path),
                bucket=bucket,
                key=key,
                metadata={
                    'collection_name': self.collection_name,
                    'backup_type': 'incremental' if incremental else 'full',
                    'persist_directory': self.persist_directory
                }
            )

        logger.info(
            "Vector store backup completed",
            bucket=bucket,
            key=key,
            backup_size=backup_size,
            etag=result.get('etag')
        )

        return {
            'success': True,
            'backup_size': backup_size,
            'bucket': bucket,
            'key': key,
            'etag': result.get('etag'),
            'incremental': incremental
        }

    def restore_from_s3(
        self,
        bucket: str,
        key: str,
        s3_client: Optional[S3Client] = None,
        overwrite: bool = True
    ) -> Dict[str, Any]:
        """
        Restore vector store from S3 backup.

        Downloads tar.gz archive from S3 and extracts to persist directory.

        Args:
            bucket: S3 bucket name
            key: S3 object key of backup
            s3_client: Optional S3Client instance
            overwrite: If True, overwrite existing persist directory

        Returns:
            Dict with success status and restore info

        Raises:
            FileExistsError: If persist directory exists and overwrite=False
            FileNotFoundError: If backup doesn't exist in S3
            S3ClientError: If S3 download fails
        """
        client = s3_client or S3Client()

        persist_path = Path(self.persist_directory)

        # Check if persist directory exists
        if persist_path.exists() and not overwrite:
            raise FileExistsError(
                f"Persist directory already exists: {self.persist_directory}. "
                "Use overwrite=True to replace it."
            )

        logger.info(
            "Starting vector store restore from S3",
            bucket=bucket,
            key=key,
            persist_directory=self.persist_directory,
            overwrite=overwrite
        )

        # Download archive to temporary location
        with tempfile.TemporaryDirectory() as tmp_dir:
            archive_path = Path(tmp_dir) / "vector-store-restore.tar.gz"

            # Download from S3
            result = client.download_file(
                bucket=bucket,
                key=key,
                file_path=str(archive_path)
            )

            download_size = result['size_bytes']

            logger.info(
                "Vector store archive downloaded",
                archive_size=download_size,
                archive_path=str(archive_path)
            )

            # Remove existing persist directory if overwrite
            if persist_path.exists() and overwrite:
                logger.info(
                    "Removing existing persist directory",
                    persist_directory=self.persist_directory
                )
                shutil.rmtree(persist_path)

            # Extract archive
            extract_dir = persist_path.parent

            with tarfile.open(archive_path, "r:gz") as tar:
                # Security check: ensure all paths are under extract_dir
                for member in tar.getmembers():
                    member_path = Path(extract_dir) / member.name
                    if not str(member_path.resolve()).startswith(str(extract_dir.resolve())):
                        raise ValueError(
                            f"Archive contains unsafe path: {member.name}"
                        )

                tar.extractall(path=extract_dir)

            logger.info(
                "Vector store restored",
                persist_directory=self.persist_directory,
                archive_size=download_size
            )

        return {
            'success': True,
            'bucket': bucket,
            'key': key,
            'download_size': download_size,
            'persist_directory': self.persist_directory
        }

    def list_backups(
        self,
        bucket: str,
        prefix: str = "backups/",
        s3_client: Optional[S3Client] = None
    ) -> List[Dict[str, Any]]:
        """
        List available backups in S3.

        Args:
            bucket: S3 bucket name
            prefix: S3 key prefix for backups
            s3_client: Optional S3Client instance

        Returns:
            List of backup metadata dicts
        """
        client = s3_client or S3Client()

        result = client.list_files(bucket=bucket, prefix=prefix)

        backups = []
        for file_info in result['files']:
            if file_info['key'].endswith('.tar.gz'):
                backups.append({
                    'key': file_info['key'],
                    'size': file_info['size'],
                    'last_modified': file_info['last_modified'],
                    'bucket': bucket
                })

        logger.info(
            "Listed vector store backups",
            bucket=bucket,
            prefix=prefix,
            backup_count=len(backups)
        )

        return backups

    def clear(self) -> None:
        """
        Clear the vector store (delete persist directory).

        WARNING: This is destructive and cannot be undone.
        """
        persist_path = Path(self.persist_directory)

        if persist_path.exists():
            logger.warning(
                "Clearing vector store",
                persist_directory=self.persist_directory
            )
            shutil.rmtree(persist_path)
            logger.info("Vector store cleared")
        else:
            logger.info(
                "Vector store already empty",
                persist_directory=self.persist_directory
            )
