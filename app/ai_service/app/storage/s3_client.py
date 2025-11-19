"""
S3Client - AWS S3 integration for BMO Learning Platform.

This module provides a clean interface for S3 operations with support for:
- LocalStack for testing/development
- Production AWS S3
- Comprehensive error handling
- Presigned URLs for secure file sharing
- Batch operations for efficiency

Usage:
    from app.storage.s3_client import S3Client

    # Initialize (automatically configures based on environment)
    client = S3Client()

    # Upload file
    result = client.upload_file(
        file_path="/path/to/document.pdf",
        bucket="my-bucket",
        key="uploads/document.pdf"
    )

    # Download file
    result = client.download_file(
        bucket="my-bucket",
        key="uploads/document.pdf",
        file_path="/path/to/save/document.pdf"
    )

Environment Variables:
    AWS_ENDPOINT_URL: Override endpoint (for LocalStack)
    AWS_ACCESS_KEY_ID: AWS access key
    AWS_SECRET_ACCESS_KEY: AWS secret key
    AWS_REGION: AWS region (default: us-east-2)
    USE_LOCALSTACK: Enable LocalStack mode (default: false)
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class S3UploadResult:
    """Result of S3 upload operation."""
    success: bool
    etag: Optional[str] = None
    version_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class S3DownloadResult:
    """Result of S3 download operation."""
    success: bool
    file_path: Optional[str] = None
    size_bytes: Optional[int] = None
    error: Optional[str] = None


class S3ClientError(Exception):
    """Base exception for S3Client errors."""
    pass


class S3Client:
    """
    AWS S3 client with LocalStack support.

    Provides high-level methods for common S3 operations with proper error handling
    and logging. Automatically configures for LocalStack when USE_LOCALSTACK=true.
    """

    # S3 bucket naming rules
    BUCKET_NAME_PATTERN = re.compile(r'^[a-z0-9][a-z0-9\-]{1,61}[a-z0-9]$')

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        region: Optional[str] = None
    ):
        """
        Initialize S3 client.

        Args:
            endpoint_url: Override endpoint URL (for LocalStack)
            access_key_id: AWS access key ID
            secret_access_key: AWS secret access key
            region: AWS region

        If parameters are None, will use environment variables.
        """
        # Get configuration from environment or parameters
        self.endpoint_url = endpoint_url or os.getenv('AWS_ENDPOINT_URL')
        self.access_key_id = access_key_id or os.getenv('AWS_ACCESS_KEY_ID')
        self.secret_access_key = secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY')
        self.region = region or os.getenv('AWS_REGION', 'us-east-2')
        self.use_localstack = os.getenv('USE_LOCALSTACK', 'false').lower() == 'true'

        # Configure boto3 client
        config = Config(
            region_name=self.region,
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            }
        )

        client_kwargs = {
            'service_name': 's3',
            'config': config
        }

        # Add credentials if provided
        if self.access_key_id and self.secret_access_key:
            client_kwargs['aws_access_key_id'] = self.access_key_id
            client_kwargs['aws_secret_access_key'] = self.secret_access_key

        # Add endpoint URL for LocalStack
        if self.endpoint_url:
            client_kwargs['endpoint_url'] = self.endpoint_url

        self.client = boto3.client(**client_kwargs)

        logger.info(
            "S3Client initialized",
            region=self.region,
            use_localstack=self.use_localstack,
            endpoint_url=self.endpoint_url
        )

    def _validate_bucket_name(self, bucket: str) -> None:
        """
        Validate S3 bucket name according to AWS rules.

        Args:
            bucket: Bucket name to validate

        Raises:
            ValueError: If bucket name is invalid
        """
        if not self.BUCKET_NAME_PATTERN.match(bucket):
            raise ValueError(
                f"Invalid bucket name: {bucket}. "
                "Bucket names must be 3-63 characters, lowercase, "
                "start/end with letter/number, and contain only letters, numbers, and hyphens."
            )

    def upload_file(
        self,
        file_path: str,
        bucket: str,
        key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Upload a file to S3.

        Args:
            file_path: Local path to file to upload
            bucket: S3 bucket name
            key: S3 object key (path in bucket)
            metadata: Optional metadata dict to attach to object

        Returns:
            Dict with success status and upload details

        Raises:
            FileNotFoundError: If file_path doesn't exist
            ValueError: If bucket name is invalid
            S3ClientError: If upload fails
        """
        self._validate_bucket_name(bucket)

        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            logger.error("File not found", file_path=file_path)
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata

            response = self.client.upload_file(
                Filename=str(file_path_obj),
                Bucket=bucket,
                Key=key,
                ExtraArgs=extra_args if extra_args else None
            )

            # Get object metadata to return ETag
            head_response = self.client.head_object(Bucket=bucket, Key=key)

            logger.info(
                "File uploaded to S3",
                file_path=file_path,
                bucket=bucket,
                key=key,
                etag=head_response.get('ETag')
            )

            return {
                'success': True,
                'etag': head_response.get('ETag'),
                'version_id': head_response.get('VersionId'),
                'key': key,
                'bucket': bucket
            }

        except ClientError as e:
            error_msg = f"Failed to upload file to S3: {e}"
            logger.error(
                "S3 upload failed",
                error=str(e),
                file_path=file_path,
                bucket=bucket,
                key=key
            )
            raise S3ClientError(error_msg) from e

    def download_file(
        self,
        bucket: str,
        key: str,
        file_path: str
    ) -> Dict[str, Any]:
        """
        Download a file from S3.

        Args:
            bucket: S3 bucket name
            key: S3 object key
            file_path: Local path where file will be saved

        Returns:
            Dict with success status and download details

        Raises:
            ClientError: If object doesn't exist (404)
            S3ClientError: If download fails
        """
        self._validate_bucket_name(bucket)

        # Ensure parent directory exists
        file_path_obj = Path(file_path)
        file_path_obj.parent.mkdir(parents=True, exist_ok=True)

        try:
            self.client.download_file(
                Bucket=bucket,
                Key=key,
                Filename=str(file_path_obj)
            )

            file_size = file_path_obj.stat().st_size

            logger.info(
                "File downloaded from S3",
                bucket=bucket,
                key=key,
                file_path=file_path,
                size_bytes=file_size
            )

            return {
                'success': True,
                'file_path': file_path,
                'size_bytes': file_size,
                'key': key,
                'bucket': bucket
            }

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(
                "S3 download failed",
                error=str(e),
                error_code=error_code,
                bucket=bucket,
                key=key
            )
            # Re-raise ClientError for 404 handling in tests
            if error_code == '404' or error_code == 'NoSuchKey':
                raise
            raise S3ClientError(f"Failed to download file from S3: {e}") from e

    def list_files(
        self,
        bucket: str,
        prefix: str = "",
        max_results: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        List files in S3 bucket with optional prefix filter.

        Args:
            bucket: S3 bucket name
            prefix: Key prefix to filter by (e.g., "documents/")
            max_results: Maximum number of results to return

        Returns:
            Dict with success status and list of file metadata
        """
        self._validate_bucket_name(bucket)

        try:
            kwargs = {
                'Bucket': bucket,
                'Prefix': prefix
            }

            if max_results:
                kwargs['MaxKeys'] = max_results

            response = self.client.list_objects_v2(**kwargs)

            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'etag': obj['ETag']
                    })

            logger.info(
                "Listed S3 files",
                bucket=bucket,
                prefix=prefix,
                count=len(files)
            )

            return {
                'success': True,
                'files': files,
                'count': len(files),
                'bucket': bucket,
                'prefix': prefix
            }

        except ClientError as e:
            logger.error(
                "S3 list files failed",
                error=str(e),
                bucket=bucket,
                prefix=prefix
            )
            raise S3ClientError(f"Failed to list files in S3: {e}") from e

    def delete_file(
        self,
        bucket: str,
        key: str
    ) -> Dict[str, Any]:
        """
        Delete a file from S3.

        Note: S3 delete is idempotent - succeeds even if file doesn't exist.

        Args:
            bucket: S3 bucket name
            key: S3 object key

        Returns:
            Dict with success status
        """
        self._validate_bucket_name(bucket)

        try:
            self.client.delete_object(
                Bucket=bucket,
                Key=key
            )

            logger.info(
                "File deleted from S3",
                bucket=bucket,
                key=key
            )

            return {
                'success': True,
                'key': key,
                'bucket': bucket
            }

        except ClientError as e:
            logger.error(
                "S3 delete failed",
                error=str(e),
                bucket=bucket,
                key=key
            )
            raise S3ClientError(f"Failed to delete file from S3: {e}") from e

    def file_exists(
        self,
        bucket: str,
        key: str
    ) -> bool:
        """
        Check if a file exists in S3.

        Args:
            bucket: S3 bucket name
            key: S3 object key

        Returns:
            True if file exists, False otherwise
        """
        try:
            self.client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404' or error_code == 'NoSuchKey':
                return False
            # Re-raise other errors
            raise

    def get_file_url(
        self,
        bucket: str,
        key: str,
        expiration: int = 3600
    ) -> Dict[str, Any]:
        """
        Generate a presigned URL for accessing an S3 file.

        Args:
            bucket: S3 bucket name
            key: S3 object key
            expiration: URL expiration time in seconds (default: 1 hour)

        Returns:
            Dict with success status and presigned URL
        """
        self._validate_bucket_name(bucket)

        try:
            url = self.client.generate_presigned_url(
                ClientMethod='get_object',
                Params={
                    'Bucket': bucket,
                    'Key': key
                },
                ExpiresIn=expiration
            )

            logger.info(
                "Generated presigned URL",
                bucket=bucket,
                key=key,
                expiration=expiration
            )

            return {
                'success': True,
                'url': url,
                'expires_in': expiration,
                'key': key,
                'bucket': bucket
            }

        except ClientError as e:
            logger.error(
                "Failed to generate presigned URL",
                error=str(e),
                bucket=bucket,
                key=key
            )
            raise S3ClientError(f"Failed to generate presigned URL: {e}") from e

    def batch_upload(
        self,
        bucket: str,
        files: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Upload multiple files to S3 in batch.

        Args:
            bucket: S3 bucket name
            files: List of dicts with 'file_path' and 'key' keys

        Returns:
            Dict with success status and upload results

        Example:
            files = [
                {'file_path': '/tmp/file1.txt', 'key': 'uploads/file1.txt'},
                {'file_path': '/tmp/file2.txt', 'key': 'uploads/file2.txt'}
            ]
            result = client.batch_upload(bucket='my-bucket', files=files)
        """
        self._validate_bucket_name(bucket)

        uploaded = []
        failed = []

        for file_info in files:
            file_path = file_info['file_path']
            key = file_info['key']

            try:
                result = self.upload_file(
                    file_path=file_path,
                    bucket=bucket,
                    key=key
                )
                uploaded.append({
                    'file_path': file_path,
                    'key': key,
                    'etag': result.get('etag')
                })
            except Exception as e:
                logger.error(
                    "Batch upload failed for file",
                    file_path=file_path,
                    key=key,
                    error=str(e)
                )
                failed.append({
                    'file_path': file_path,
                    'key': key,
                    'error': str(e)
                })

        logger.info(
            "Batch upload completed",
            bucket=bucket,
            total=len(files),
            uploaded=len(uploaded),
            failed=len(failed)
        )

        return {
            'success': len(failed) == 0,
            'uploaded_count': len(uploaded),
            'failed_count': len(failed),
            'uploaded': uploaded,
            'failed': failed,
            'bucket': bucket
        }
