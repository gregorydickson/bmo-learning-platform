# frozen_string_literal: true

require 'aws-sdk-s3'

##
# S3Service - AWS S3 integration for BMO Learning Platform (Rails)
#
# Provides a clean interface for S3 operations with:
# - LocalStack support for testing
# - Dry::Monads for functional error handling
# - Comprehensive logging
# - Presigned URL generation
#
# Usage:
#   service = S3Service.new
#
#   # Upload file
#   result = service.upload_file(
#     file_path: '/path/to/file.pdf',
#     bucket: 'bmo-learning-documents',
#     key: 'uploads/lesson.pdf'
#   )
#
#   case result
#   in Success(data)
#     puts "Uploaded: #{data[:etag]}"
#   in Failure(error)
#     puts "Failed: #{error}"
#   end
#
class S3Service
  include Dry::Monads[:result]

  # S3 bucket naming validation pattern
  BUCKET_NAME_PATTERN = /\A[a-z0-9][a-z0-9\-]{1,61}[a-z0-9]\z/

  attr_reader :client, :use_localstack

  ##
  # Initialize S3Service
  #
  # Automatically configures for LocalStack if USE_LOCALSTACK=true
  #
  # @param endpoint_url [String, nil] Override endpoint URL (for LocalStack)
  # @param access_key_id [String, nil] AWS access key ID
  # @param secret_access_key [String, nil] AWS secret access key
  # @param region [String] AWS region (default: us-east-2)
  #
  def initialize(
    endpoint_url: nil,
    access_key_id: nil,
    secret_access_key: nil,
    region: nil
  )
    @endpoint_url = endpoint_url || ENV['AWS_ENDPOINT_URL']
    @access_key_id = access_key_id || ENV['AWS_ACCESS_KEY_ID']
    @secret_access_key = secret_access_key || ENV['AWS_SECRET_ACCESS_KEY']
    @region = region || ENV.fetch('AWS_REGION', 'us-east-2')
    @use_localstack = ENV.fetch('USE_LOCALSTACK', 'false') == 'true'

    @client = build_client

    Rails.logger.info(
      "[S3Service] Initialized",
      region: @region,
      use_localstack: @use_localstack,
      endpoint_url: @endpoint_url
    )
  end

  ##
  # Upload a file to S3
  #
  # @param file_path [String] Local path to file
  # @param bucket [String] S3 bucket name
  # @param key [String] S3 object key (path in bucket)
  # @param metadata [Hash] Optional metadata to attach
  # @param content_type [String] Optional content type
  #
  # @return [Dry::Monads::Result] Success with upload data or Failure with error
  #
  # @example
  #   result = service.upload_file(
  #     file_path: '/tmp/doc.pdf',
  #     bucket: 'my-bucket',
  #     key: 'uploads/doc.pdf',
  #     metadata: { 'learner-id' => '123' }
  #   )
  #
  def upload_file(file_path:, bucket:, key:, metadata: {}, content_type: nil)
    return Failure("File not found: #{file_path}") unless File.exist?(file_path)
    return Failure("Invalid bucket name: #{bucket}") unless valid_bucket_name?(bucket)

    Rails.logger.info(
      "[S3Service] Uploading file",
      file_path: file_path,
      bucket: bucket,
      key: key
    )

    File.open(file_path, 'rb') do |file|
      options = {
        bucket: bucket,
        key: key,
        body: file
      }

      options[:metadata] = metadata if metadata.any?
      options[:content_type] = content_type if content_type

      response = @client.put_object(**options)

      # Get object metadata
      head_response = @client.head_object(bucket: bucket, key: key)

      Rails.logger.info(
        "[S3Service] File uploaded successfully",
        bucket: bucket,
        key: key,
        etag: head_response.etag
      )

      Success({
        success: true,
        bucket: bucket,
        key: key,
        etag: head_response.etag,
        version_id: head_response.version_id,
        size: head_response.content_length
      })
    end
  rescue Aws::S3::Errors::ServiceError => e
    Rails.logger.error(
      "[S3Service] Upload failed",
      error: e.message,
      bucket: bucket,
      key: key
    )
    Failure("S3 upload failed: #{e.message}")
  rescue StandardError => e
    Rails.logger.error("[S3Service] Unexpected error", error: e.message)
    Failure("Upload failed: #{e.message}")
  end

  ##
  # Download a file from S3
  #
  # @param bucket [String] S3 bucket name
  # @param key [String] S3 object key
  # @param file_path [String] Local path where file will be saved
  #
  # @return [Dry::Monads::Result] Success with download data or Failure with error
  #
  def download_file(bucket:, key:, file_path:)
    return Failure("Invalid bucket name: #{bucket}") unless valid_bucket_name?(bucket)

    Rails.logger.info(
      "[S3Service] Downloading file",
      bucket: bucket,
      key: key,
      file_path: file_path
    )

    # Ensure parent directory exists
    FileUtils.mkdir_p(File.dirname(file_path))

    @client.get_object(
      bucket: bucket,
      key: key,
      response_target: file_path
    )

    file_size = File.size(file_path)

    Rails.logger.info(
      "[S3Service] File downloaded successfully",
      bucket: bucket,
      key: key,
      size: file_size
    )

    Success({
      success: true,
      bucket: bucket,
      key: key,
      file_path: file_path,
      size: file_size
    })
  rescue Aws::S3::Errors::NoSuchKey
    Rails.logger.error("[S3Service] File not found", bucket: bucket, key: key)
    Failure("File not found in S3: #{key}")
  rescue Aws::S3::Errors::ServiceError => e
    Rails.logger.error("[S3Service] Download failed", error: e.message)
    Failure("S3 download failed: #{e.message}")
  rescue StandardError => e
    Rails.logger.error("[S3Service] Unexpected error", error: e.message)
    Failure("Download failed: #{e.message}")
  end

  ##
  # List files in S3 bucket with optional prefix filter
  #
  # @param bucket [String] S3 bucket name
  # @param prefix [String] Key prefix to filter by
  # @param max_results [Integer] Maximum number of results
  #
  # @return [Dry::Monads::Result] Success with file list or Failure with error
  #
  def list_files(bucket:, prefix: '', max_results: 1000)
    return Failure("Invalid bucket name: #{bucket}") unless valid_bucket_name?(bucket)

    Rails.logger.info(
      "[S3Service] Listing files",
      bucket: bucket,
      prefix: prefix
    )

    response = @client.list_objects_v2(
      bucket: bucket,
      prefix: prefix,
      max_keys: max_results
    )

    files = response.contents.map do |object|
      {
        key: object.key,
        size: object.size,
        last_modified: object.last_modified,
        etag: object.etag
      }
    end

    Rails.logger.info(
      "[S3Service] Files listed",
      bucket: bucket,
      count: files.size
    )

    Success({
      success: true,
      bucket: bucket,
      prefix: prefix,
      files: files,
      count: files.size
    })
  rescue Aws::S3::Errors::ServiceError => e
    Rails.logger.error("[S3Service] List failed", error: e.message)
    Failure("S3 list failed: #{e.message}")
  end

  ##
  # Delete a file from S3
  #
  # Note: S3 delete is idempotent (succeeds even if file doesn't exist)
  #
  # @param bucket [String] S3 bucket name
  # @param key [String] S3 object key
  #
  # @return [Dry::Monads::Result] Success or Failure
  #
  def delete_file(bucket:, key:)
    return Failure("Invalid bucket name: #{bucket}") unless valid_bucket_name?(bucket)

    Rails.logger.info(
      "[S3Service] Deleting file",
      bucket: bucket,
      key: key
    )

    @client.delete_object(bucket: bucket, key: key)

    Rails.logger.info(
      "[S3Service] File deleted",
      bucket: bucket,
      key: key
    )

    Success({
      success: true,
      bucket: bucket,
      key: key
    })
  rescue Aws::S3::Errors::ServiceError => e
    Rails.logger.error("[S3Service] Delete failed", error: e.message)
    Failure("S3 delete failed: #{e.message}")
  end

  ##
  # Check if a file exists in S3
  #
  # @param bucket [String] S3 bucket name
  # @param key [String] S3 object key
  #
  # @return [Boolean] True if file exists, false otherwise
  #
  def file_exists?(bucket:, key:)
    @client.head_object(bucket: bucket, key: key)
    true
  rescue Aws::S3::Errors::NotFound
    false
  rescue Aws::S3::Errors::ServiceError => e
    Rails.logger.error("[S3Service] Exists check failed", error: e.message)
    false
  end

  ##
  # Generate a presigned URL for accessing an S3 file
  #
  # @param bucket [String] S3 bucket name
  # @param key [String] S3 object key
  # @param expiration [Integer] URL expiration time in seconds (default: 3600 = 1 hour)
  #
  # @return [Dry::Monads::Result] Success with URL or Failure with error
  #
  # @example
  #   result = service.get_presigned_url(
  #     bucket: 'my-bucket',
  #     key: 'uploads/doc.pdf',
  #     expiration: 7200  # 2 hours
  #   )
  #
  def get_presigned_url(bucket:, key:, expiration: 3600)
    return Failure("Invalid bucket name: #{bucket}") unless valid_bucket_name?(bucket)

    Rails.logger.info(
      "[S3Service] Generating presigned URL",
      bucket: bucket,
      key: key,
      expiration: expiration
    )

    url = @client.presigned_url(
      :get_object,
      bucket: bucket,
      key: key,
      expires_in: expiration
    )

    Rails.logger.info(
      "[S3Service] Presigned URL generated",
      bucket: bucket,
      key: key
    )

    Success({
      success: true,
      url: url,
      expires_in: expiration,
      bucket: bucket,
      key: key
    })
  rescue Aws::S3::Errors::ServiceError => e
    Rails.logger.error("[S3Service] Presigned URL failed", error: e.message)
    Failure("Failed to generate presigned URL: #{e.message}")
  end

  ##
  # Upload multiple files in batch
  #
  # @param files [Array<Hash>] Array of file specs: { file_path:, key: }
  # @param bucket [String] S3 bucket name
  #
  # @return [Dry::Monads::Result] Success with batch results or Failure
  #
  # @example
  #   files = [
  #     { file_path: '/tmp/doc1.pdf', key: 'uploads/doc1.pdf' },
  #     { file_path: '/tmp/doc2.pdf', key: 'uploads/doc2.pdf' }
  #   ]
  #   result = service.batch_upload(files: files, bucket: 'my-bucket')
  #
  def batch_upload(files:, bucket:)
    uploaded = []
    failed = []

    files.each do |file_spec|
      result = upload_file(
        file_path: file_spec[:file_path],
        bucket: bucket,
        key: file_spec[:key],
        metadata: file_spec[:metadata] || {}
      )

      case result
      in Success(data)
        uploaded << data
      in Failure(error)
        failed << { file_path: file_spec[:file_path], error: error }
      end
    end

    Rails.logger.info(
      "[S3Service] Batch upload complete",
      total: files.size,
      uploaded: uploaded.size,
      failed: failed.size
    )

    Success({
      success: failed.empty?,
      uploaded_count: uploaded.size,
      failed_count: failed.size,
      uploaded: uploaded,
      failed: failed,
      bucket: bucket
    })
  end

  private

  ##
  # Build AWS S3 client with appropriate configuration
  #
  # @return [Aws::S3::Client]
  #
  def build_client
    options = {
      region: @region
    }

    # Add credentials if provided
    if @access_key_id && @secret_access_key
      options[:credentials] = Aws::Credentials.new(
        @access_key_id,
        @secret_access_key
      )
    end

    # Add endpoint URL for LocalStack
    options[:endpoint] = @endpoint_url if @endpoint_url

    # Force path style for LocalStack compatibility
    options[:force_path_style] = true if @use_localstack

    Aws::S3::Client.new(**options)
  end

  ##
  # Validate S3 bucket name according to AWS rules
  #
  # @param bucket [String] Bucket name to validate
  # @return [Boolean] True if valid, false otherwise
  #
  def valid_bucket_name?(bucket)
    bucket.match?(BUCKET_NAME_PATTERN)
  end
end
