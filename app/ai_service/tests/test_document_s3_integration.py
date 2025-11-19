"""
Integration tests for Document Processing with S3 storage.

Tests the complete document pipeline:
1. Upload document to S3
2. Load document from S3
3. Process and chunk document
4. Store embeddings in vector store
5. Backup vector store to S3
6. Restore vector store from S3

Following TDD approach - tests written first, then implementation.
"""

import os
import tempfile
from pathlib import Path

import pytest
from langchain_core.documents import Document

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestS3DocumentLoading:
    """Test loading documents directly from S3."""

    def test_load_single_pdf_from_s3(
        self,
        s3_client,
        s3_test_bucket,
        localstack_s3,
        document_processor
    ):
        """
        Test loading a single PDF from S3.

        TDD: This will fail until S3DocumentLoader is implemented.
        """
        # Arrange: Upload a test PDF to S3
        test_pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nTest PDF content"
        localstack_s3.put_object(
            Bucket=s3_test_bucket,
            Key="documents/test-lesson.pdf",
            Body=test_pdf_content
        )

        # Act: Load document from S3
        s3_uri = f"s3://{s3_test_bucket}/documents/test-lesson.pdf"
        documents = document_processor.process_s3_file(
            s3_uri=s3_uri,
            file_type="pdf"
        )

        # Assert: Document loaded successfully
        assert len(documents) > 0
        assert isinstance(documents[0], Document)
        assert documents[0].metadata.get('source') == s3_uri

    def test_load_text_file_from_s3(
        self,
        s3_client,
        s3_test_bucket,
        localstack_s3,
        document_processor
    ):
        """
        Test loading a text file from S3.

        TDD: This will fail until text file S3 loading is implemented.
        """
        # Arrange: Upload a test text file
        test_content = """
        # Python Functions Tutorial

        Functions are reusable blocks of code.
        They help organize code and make it maintainable.
        """
        localstack_s3.put_object(
            Bucket=s3_test_bucket,
            Key="documents/python-tutorial.txt",
            Body=test_content.encode('utf-8')
        )

        # Act: Load document from S3
        s3_uri = f"s3://{s3_test_bucket}/documents/python-tutorial.txt"
        documents = document_processor.process_s3_file(
            s3_uri=s3_uri,
            file_type="txt"
        )

        # Assert: Document loaded successfully
        assert len(documents) == 1
        assert "Functions are reusable" in documents[0].page_content
        assert documents[0].metadata.get('source') == s3_uri

    def test_load_s3_directory(
        self,
        s3_client,
        s3_test_bucket,
        localstack_s3,
        document_processor
    ):
        """
        Test loading all documents from an S3 prefix (directory).

        TDD: This will fail until S3 directory loading is implemented.
        """
        # Arrange: Upload multiple test files
        test_files = {
            "lessons/python-basics.txt": "Python is a programming language.",
            "lessons/python-functions.txt": "Functions are defined with def keyword.",
            "lessons/python-classes.txt": "Classes are blueprints for objects."
        }

        for key, content in test_files.items():
            localstack_s3.put_object(
                Bucket=s3_test_bucket,
                Key=key,
                Body=content.encode('utf-8')
            )

        # Act: Load all documents from S3 prefix
        s3_uri = f"s3://{s3_test_bucket}/lessons/"
        documents = document_processor.process_s3_directory(
            s3_uri=s3_uri,
            file_type="txt"
        )

        # Assert: All documents loaded
        assert len(documents) == 3
        contents = [doc.page_content for doc in documents]
        assert any("programming language" in c for c in contents)
        assert any("def keyword" in c for c in contents)
        assert any("blueprints" in c for c in contents)

    def test_s3_file_not_found(self, s3_test_bucket, document_processor):
        """
        Test handling of non-existent S3 files.

        TDD: This will fail until error handling is implemented.
        """
        # Act & Assert: Should raise appropriate error
        s3_uri = f"s3://{s3_test_bucket}/nonexistent/file.pdf"
        with pytest.raises(FileNotFoundError):
            document_processor.process_s3_file(s3_uri=s3_uri, file_type="pdf")

    def test_invalid_s3_uri_format(self, document_processor):
        """
        Test handling of invalid S3 URI format.

        TDD: This will fail until URI validation is implemented.
        """
        # Act & Assert: Should raise ValueError
        with pytest.raises(ValueError):
            document_processor.process_s3_file(
                s3_uri="invalid-uri-format",
                file_type="pdf"
            )


class TestDocumentProcessingPipeline:
    """Test complete end-to-end document processing pipeline."""

    def test_e2e_upload_process_embed(
        self,
        s3_client,
        s3_test_bucket,
        localstack_s3,
        document_processor,
        vector_store_manager
    ):
        """
        Test complete pipeline: S3 upload → process → chunk → embed → store.

        TDD: This will fail until full pipeline is integrated.
        """
        # Arrange: Create test document
        test_content = """
        Machine Learning Basics

        Machine learning is a subset of artificial intelligence.
        It enables computers to learn from data without being explicitly programmed.

        Types of Machine Learning:
        1. Supervised Learning
        2. Unsupervised Learning
        3. Reinforcement Learning
        """

        # Upload to S3
        s3_client.upload_file(
            file_path=self._create_temp_file(test_content),
            bucket=s3_test_bucket,
            key="lessons/ml-basics.txt"
        )

        # Act: Process document from S3
        s3_uri = f"s3://{s3_test_bucket}/lessons/ml-basics.txt"
        documents = document_processor.process_s3_file(
            s3_uri=s3_uri,
            file_type="txt"
        )

        # Chunk documents
        chunks = document_processor.chunk_documents(documents)

        # Add to vector store
        vector_store_manager.add_documents(chunks)

        # Assert: Documents processed and embedded
        assert len(chunks) > 0

        # Verify documents in vector store
        results = vector_store_manager.search(
            query="What is machine learning?",
            k=3
        )
        assert len(results) > 0
        assert any("subset of artificial intelligence" in r.page_content for r in results)

    def test_batch_s3_document_processing(
        self,
        s3_client,
        s3_test_bucket,
        document_processor
    ):
        """
        Test processing multiple S3 documents in batch.

        TDD: This will fail until batch processing is implemented.
        """
        # Arrange: Upload multiple documents
        documents_to_upload = [
            ("lessons/python-1.txt", "Python basics content"),
            ("lessons/python-2.txt", "Python functions content"),
            ("lessons/python-3.txt", "Python classes content"),
        ]

        for key, content in documents_to_upload:
            temp_file = self._create_temp_file(content)
            s3_client.upload_file(
                file_path=temp_file,
                bucket=s3_test_bucket,
                key=key
            )

        # Act: Batch process S3 URIs
        s3_uris = [f"s3://{s3_test_bucket}/{key}" for key, _ in documents_to_upload]
        results = document_processor.batch_process_s3_files(
            s3_uris=s3_uris,
            file_type="txt"
        )

        # Assert: All documents processed
        assert results['success_count'] == 3
        assert results['failed_count'] == 0
        assert len(results['documents']) >= 3

    @staticmethod
    def _create_temp_file(content: str) -> str:
        """Helper to create temporary file with content."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(content)
            return f.name


class TestVectorStoreS3Backup:
    """Test vector store backup and restore to/from S3."""

    def test_backup_vector_store_to_s3(
        self,
        s3_client,
        s3_test_bucket,
        vector_store_manager
    ):
        """
        Test backing up vector store to S3.

        TDD: This will fail until backup functionality is implemented.
        """
        # Arrange: Add some documents to vector store
        documents = [
            Document(page_content="Python is a programming language", metadata={"topic": "python"}),
            Document(page_content="JavaScript is used for web development", metadata={"topic": "javascript"}),
            Document(page_content="SQL is for database queries", metadata={"topic": "sql"})
        ]
        vector_store_manager.add_documents(documents)

        # Act: Backup to S3
        backup_key = "backups/vector-store-backup.tar.gz"
        result = vector_store_manager.backup_to_s3(
            bucket=s3_test_bucket,
            key=backup_key
        )

        # Assert: Backup successful
        assert result['success'] is True
        assert result['backup_size'] > 0

        # Verify backup exists in S3
        assert s3_client.file_exists(bucket=s3_test_bucket, key=backup_key)

    def test_restore_vector_store_from_s3(
        self,
        s3_client,
        s3_test_bucket,
        vector_store_manager
    ):
        """
        Test restoring vector store from S3 backup.

        TDD: This will fail until restore functionality is implemented.
        """
        # Arrange: Create backup
        original_docs = [
            Document(page_content="Test document 1", metadata={"id": "1"}),
            Document(page_content="Test document 2", metadata={"id": "2"}),
        ]
        vector_store_manager.add_documents(original_docs)

        backup_key = "backups/test-restore.tar.gz"
        vector_store_manager.backup_to_s3(
            bucket=s3_test_bucket,
            key=backup_key
        )

        # Clear vector store
        vector_store_manager.clear()

        # Act: Restore from S3
        result = vector_store_manager.restore_from_s3(
            bucket=s3_test_bucket,
            key=backup_key
        )

        # Assert: Restore successful
        assert result['success'] is True

        # Verify documents restored
        search_results = vector_store_manager.search("Test document", k=5)
        assert len(search_results) == 2

    def test_incremental_backup(
        self,
        s3_client,
        s3_test_bucket,
        vector_store_manager
    ):
        """
        Test incremental backup (only new/modified documents).

        TDD: This will fail until incremental backup is implemented.
        """
        # Arrange: Initial backup
        docs_v1 = [
            Document(page_content="Version 1 doc", metadata={"version": "1"})
        ]
        vector_store_manager.add_documents(docs_v1)
        vector_store_manager.backup_to_s3(
            bucket=s3_test_bucket,
            key="backups/v1.tar.gz"
        )

        # Add more documents
        docs_v2 = [
            Document(page_content="Version 2 doc", metadata={"version": "2"})
        ]
        vector_store_manager.add_documents(docs_v2)

        # Act: Incremental backup
        result = vector_store_manager.backup_to_s3(
            bucket=s3_test_bucket,
            key="backups/v2-incremental.tar.gz",
            incremental=True
        )

        # Assert: Incremental backup smaller than full backup
        assert result['success'] is True
        # Incremental should only contain new documents


class TestMixedSources:
    """Test processing documents from both filesystem and S3."""

    def test_process_mixed_sources(
        self,
        s3_client,
        s3_test_bucket,
        document_processor,
        tmp_path
    ):
        """
        Test processing documents from both local filesystem and S3.

        TDD: This will fail until mixed source support is implemented.
        """
        # Arrange: Local file
        local_file = tmp_path / "local-doc.txt"
        local_file.write_text("This is a local document")

        # S3 file
        s3_client.upload_file(
            file_path=self._create_temp_file("This is an S3 document"),
            bucket=s3_test_bucket,
            key="remote-doc.txt"
        )

        # Act: Process both sources
        sources = [
            {"type": "local", "path": str(local_file)},
            {"type": "s3", "uri": f"s3://{s3_test_bucket}/remote-doc.txt"}
        ]

        result = document_processor.process_multiple_sources(sources)

        # Assert: Both sources processed
        assert result['success_count'] == 2
        assert len(result['documents']) == 2

        contents = [doc.page_content for doc in result['documents']]
        assert "local document" in contents[0] or "local document" in contents[1]
        assert "S3 document" in contents[0] or "S3 document" in contents[1]

    @staticmethod
    def _create_temp_file(content: str) -> str:
        """Helper to create temporary file with content."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(content)
            return f.name


# ===================================================
# Additional Test Fixtures
# ===================================================

@pytest.fixture
def document_processor():
    """Document processor instance for testing."""
    from app.ingestion.document_processor import DocumentProcessor
    return DocumentProcessor(chunk_size=500, chunk_overlap=50)


@pytest.fixture
def vector_store_manager(temp_chroma_dir):
    """Vector store manager for testing."""
    from app.ingestion.vector_store import VectorStoreManager
    return VectorStoreManager(persist_directory=temp_chroma_dir)


@pytest.fixture
def temp_chroma_dir():
    """Temporary directory for Chroma persistence."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir
