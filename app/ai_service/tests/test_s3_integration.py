"""
Integration tests for S3Client with LocalStack.

Following TDD approach:
1. Write failing tests first
2. Implement S3Client to make tests pass
3. Refactor as needed

These tests require LocalStack running on localhost:4566
Run with: pytest -m integration

Marking tests with @pytest.mark.integration allows separation:
- Unit tests (fast, mocked): pytest -m "not integration"
- Integration tests (slower, LocalStack): pytest -m integration
"""

import os
import tempfile
from pathlib import Path

import boto3
import pytest
from botocore.exceptions import ClientError

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestS3ClientIntegration:
    """Integration tests for S3Client using LocalStack."""

    def test_upload_file_success(self, s3_client, s3_test_bucket, localstack_s3):
        """
        Test uploading a file to S3 successfully.

        TDD: This will fail until S3Client.upload_file() is implemented.
        """
        # Arrange: Create a temporary test file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as tmp_file:
            tmp_file.write("This is a test document for BMO Learning Platform.")
            tmp_file_path = tmp_file.name

        try:
            # Act: Upload file using S3Client
            result = s3_client.upload_file(
                file_path=tmp_file_path,
                bucket=s3_test_bucket,
                key="uploads/test-document.txt"
            )

            # Assert: Upload succeeded
            assert result is not None
            assert result.get('success') is True
            assert 'etag' in result or 'ETag' in result

            # Verify file exists in LocalStack S3
            response = localstack_s3.head_object(
                Bucket=s3_test_bucket,
                Key="uploads/test-document.txt"
            )
            assert response['ResponseMetadata']['HTTPStatusCode'] == 200

        finally:
            # Cleanup
            os.unlink(tmp_file_path)

    def test_upload_file_with_metadata(self, s3_client, s3_test_bucket, localstack_s3):
        """
        Test uploading a file with custom metadata.

        TDD: This will fail until metadata support is implemented.
        """
        # Arrange
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as tmp_file:
            tmp_file.write("Document with metadata")
            tmp_file_path = tmp_file.name

        metadata = {
            'learner-id': '12345',
            'topic': 'python-basics',
            'difficulty': 'beginner'
        }

        try:
            # Act
            result = s3_client.upload_file(
                file_path=tmp_file_path,
                bucket=s3_test_bucket,
                key="uploads/document-with-metadata.txt",
                metadata=metadata
            )

            # Assert
            assert result['success'] is True

            # Verify metadata in S3
            response = localstack_s3.head_object(
                Bucket=s3_test_bucket,
                Key="uploads/document-with-metadata.txt"
            )
            assert response['Metadata']['learner-id'] == '12345'
            assert response['Metadata']['topic'] == 'python-basics'

        finally:
            os.unlink(tmp_file_path)

    def test_upload_file_not_found(self, s3_client, s3_test_bucket):
        """
        Test uploading a non-existent file raises appropriate error.

        TDD: This will fail until error handling is implemented.
        """
        # Act & Assert
        with pytest.raises(FileNotFoundError):
            s3_client.upload_file(
                file_path="/nonexistent/file.txt",
                bucket=s3_test_bucket,
                key="uploads/missing.txt"
            )

    def test_download_file_success(self, s3_client, s3_test_bucket, localstack_s3):
        """
        Test downloading a file from S3 successfully.

        TDD: This will fail until S3Client.download_file() is implemented.
        """
        # Arrange: Upload a test file directly to LocalStack
        test_content = "This is test content for download."
        localstack_s3.put_object(
            Bucket=s3_test_bucket,
            Key="downloads/test-file.txt",
            Body=test_content.encode('utf-8')
        )

        # Act: Download file using S3Client
        with tempfile.TemporaryDirectory() as tmp_dir:
            download_path = os.path.join(tmp_dir, "downloaded.txt")
            result = s3_client.download_file(
                bucket=s3_test_bucket,
                key="downloads/test-file.txt",
                file_path=download_path
            )

            # Assert: Download succeeded and content matches
            assert result['success'] is True
            assert os.path.exists(download_path)

            with open(download_path, 'r') as f:
                downloaded_content = f.read()
            assert downloaded_content == test_content

    def test_download_file_not_found(self, s3_client, s3_test_bucket):
        """
        Test downloading a non-existent file raises appropriate error.

        TDD: This will fail until error handling is implemented.
        """
        # Act & Assert
        with tempfile.TemporaryDirectory() as tmp_dir:
            download_path = os.path.join(tmp_dir, "nonexistent.txt")
            with pytest.raises(ClientError) as exc_info:
                s3_client.download_file(
                    bucket=s3_test_bucket,
                    key="nonexistent/file.txt",
                    file_path=download_path
                )
            assert exc_info.value.response['Error']['Code'] == '404'

    def test_list_files_in_bucket(self, s3_client, s3_test_bucket, localstack_s3):
        """
        Test listing files in a bucket/prefix.

        TDD: This will fail until S3Client.list_files() is implemented.
        """
        # Arrange: Upload multiple test files
        test_files = [
            "documents/lesson-1.txt",
            "documents/lesson-2.txt",
            "documents/quiz-1.txt",
            "backups/backup-1.txt"
        ]

        for key in test_files:
            localstack_s3.put_object(
                Bucket=s3_test_bucket,
                Key=key,
                Body=f"Content of {key}".encode('utf-8')
            )

        # Act: List files with prefix
        result = s3_client.list_files(
            bucket=s3_test_bucket,
            prefix="documents/"
        )

        # Assert: Only documents/ files returned
        assert result['success'] is True
        assert len(result['files']) == 3

        file_keys = [f['key'] for f in result['files']]
        assert "documents/lesson-1.txt" in file_keys
        assert "documents/lesson-2.txt" in file_keys
        assert "documents/quiz-1.txt" in file_keys
        assert "backups/backup-1.txt" not in file_keys

    def test_list_files_empty_bucket(self, s3_client, s3_test_bucket):
        """
        Test listing files in an empty bucket returns empty list.

        TDD: This will fail until S3Client.list_files() handles empty buckets.
        """
        # Act
        result = s3_client.list_files(
            bucket=s3_test_bucket,
            prefix="empty/"
        )

        # Assert
        assert result['success'] is True
        assert len(result['files']) == 0

    def test_delete_file_success(self, s3_client, s3_test_bucket, localstack_s3):
        """
        Test deleting a file from S3 successfully.

        TDD: This will fail until S3Client.delete_file() is implemented.
        """
        # Arrange: Upload a test file
        test_key = "temp/file-to-delete.txt"
        localstack_s3.put_object(
            Bucket=s3_test_bucket,
            Key=test_key,
            Body=b"Temporary file"
        )

        # Verify file exists
        response = localstack_s3.head_object(Bucket=s3_test_bucket, Key=test_key)
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200

        # Act: Delete file
        result = s3_client.delete_file(
            bucket=s3_test_bucket,
            key=test_key
        )

        # Assert: Delete succeeded
        assert result['success'] is True

        # Verify file no longer exists
        with pytest.raises(ClientError) as exc_info:
            localstack_s3.head_object(Bucket=s3_test_bucket, Key=test_key)
        assert exc_info.value.response['Error']['Code'] == '404'

    def test_delete_file_not_found(self, s3_client, s3_test_bucket):
        """
        Test deleting a non-existent file (should succeed silently per S3 behavior).

        TDD: This will fail until delete behavior matches S3.
        """
        # Act: Delete non-existent file
        result = s3_client.delete_file(
            bucket=s3_test_bucket,
            key="nonexistent/file.txt"
        )

        # Assert: S3 delete is idempotent (succeeds even if file doesn't exist)
        assert result['success'] is True

    def test_file_exists_check(self, s3_client, s3_test_bucket, localstack_s3):
        """
        Test checking if a file exists in S3.

        TDD: This will fail until S3Client.file_exists() is implemented.
        """
        # Arrange: Upload a test file
        test_key = "check/exists.txt"
        localstack_s3.put_object(
            Bucket=s3_test_bucket,
            Key=test_key,
            Body=b"File content"
        )

        # Act & Assert: File exists
        assert s3_client.file_exists(bucket=s3_test_bucket, key=test_key) is True

        # Act & Assert: File does not exist
        assert s3_client.file_exists(
            bucket=s3_test_bucket,
            key="check/nonexistent.txt"
        ) is False

    def test_get_file_url(self, s3_client, s3_test_bucket, localstack_s3):
        """
        Test generating a presigned URL for S3 file.

        TDD: This will fail until S3Client.get_file_url() is implemented.
        """
        # Arrange: Upload a test file
        test_key = "shared/document.txt"
        test_content = "Shared document content"
        localstack_s3.put_object(
            Bucket=s3_test_bucket,
            Key=test_key,
            Body=test_content.encode('utf-8')
        )

        # Act: Generate presigned URL (valid for 1 hour)
        result = s3_client.get_file_url(
            bucket=s3_test_bucket,
            key=test_key,
            expiration=3600
        )

        # Assert: URL generated
        assert result['success'] is True
        assert 'url' in result
        assert test_key in result['url']

        # Verify URL works (download file via HTTP)
        import httpx
        response = httpx.get(result['url'])
        assert response.status_code == 200
        assert response.text == test_content

    def test_batch_upload(self, s3_client, s3_test_bucket, localstack_s3):
        """
        Test uploading multiple files in batch.

        TDD: This will fail until S3Client.batch_upload() is implemented.
        """
        # Arrange: Create multiple temp files
        temp_files = []
        for i in range(3):
            tmp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
            tmp_file.write(f"Batch upload test file {i}")
            tmp_file.close()
            temp_files.append({
                'file_path': tmp_file.name,
                'key': f"batch/file-{i}.txt"
            })

        try:
            # Act: Batch upload
            result = s3_client.batch_upload(
                bucket=s3_test_bucket,
                files=temp_files
            )

            # Assert: All uploads succeeded
            assert result['success'] is True
            assert result['uploaded_count'] == 3
            assert len(result['failed']) == 0

            # Verify files in S3
            for file_info in temp_files:
                response = localstack_s3.head_object(
                    Bucket=s3_test_bucket,
                    Key=file_info['key']
                )
                assert response['ResponseMetadata']['HTTPStatusCode'] == 200

        finally:
            # Cleanup
            for file_info in temp_files:
                os.unlink(file_info['file_path'])


class TestS3ClientErrorHandling:
    """Test error handling and edge cases for S3Client."""

    def test_invalid_bucket_name(self, s3_client):
        """
        Test handling of invalid bucket names.

        TDD: This will fail until validation is implemented.
        """
        with pytest.raises(ValueError):
            s3_client.upload_file(
                file_path="/tmp/test.txt",
                bucket="Invalid Bucket Name!",  # Invalid: spaces and special chars
                key="test.txt"
            )

    def test_connection_error_handling(self, monkeypatch):
        """
        Test handling of connection errors to LocalStack/S3.

        TDD: This will fail until network error handling is implemented.
        """
        # This test will need to be implemented after S3Client exists
        # Will mock boto3 to raise connection errors
        pass

    def test_large_file_upload(self, s3_client, s3_test_bucket):
        """
        Test uploading a large file (multipart upload).

        TDD: This will fail until large file handling is implemented.
        """
        # Create a 10MB test file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as tmp_file:
            tmp_file.write(b'X' * (10 * 1024 * 1024))  # 10MB
            tmp_file_path = tmp_file.name

        try:
            # Act
            result = s3_client.upload_file(
                file_path=tmp_file_path,
                bucket=s3_test_bucket,
                key="large/10mb-file.bin"
            )

            # Assert
            assert result['success'] is True

        finally:
            os.unlink(tmp_file_path)


# ===================================================
# Test Configuration Notes
# ===================================================
# Run integration tests:
#   pytest -m integration
#
# Run unit tests only:
#   pytest -m "not integration"
#
# Run all tests:
#   pytest
#
# Requirements:
#   - LocalStack running on localhost:4566
#   - S3 service enabled in LocalStack
#   - Test fixtures defined in conftest.py
