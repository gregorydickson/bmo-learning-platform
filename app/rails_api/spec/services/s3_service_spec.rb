# frozen_string_literal: true

require 'rails_helper'

RSpec.describe S3Service, type: :service do
  let(:service) { described_class.new }
  let(:test_bucket) { "test-bucket-#{SecureRandom.hex(6)}" }
  let(:localstack_client) do
    Aws::S3::Client.new(
      endpoint: ENV.fetch('AWS_ENDPOINT_URL', 'http://localhost:4566'),
      access_key_id: 'test',
      secret_access_key: 'test',
      region: 'us-east-2',
      force_path_style: true
    )
  end

  # Only run these tests if LocalStack is available
  before(:all) do
    begin
      client = Aws::S3::Client.new(
        endpoint: ENV['AWS_ENDPOINT_URL'] || 'http://localhost:4566',
        access_key_id: 'test',
        secret_access_key: 'test',
        region: 'us-east-2',
        force_path_style: true
      )
      client.list_buckets
    rescue StandardError => e
      skip "LocalStack not available: #{e.message}"
    end
  end

  before(:each) do
    # Create test bucket
    localstack_client.create_bucket(
      bucket: test_bucket,
      create_bucket_configuration: { location_constraint: 'us-east-2' }
    )
  end

  after(:each) do
    # Cleanup: Delete all objects then bucket
    begin
      response = localstack_client.list_objects_v2(bucket: test_bucket)
      if response.contents.any?
        objects = response.contents.map { |obj| { key: obj.key } }
        localstack_client.delete_objects(
          bucket: test_bucket,
          delete: { objects: objects }
        )
      end
      localstack_client.delete_bucket(bucket: test_bucket)
    rescue StandardError => e
      Rails.logger.warn("Cleanup failed: #{e.message}")
    end
  end

  describe '#initialize' do
    it 'initializes with LocalStack configuration' do
      expect(service.use_localstack).to be_truthy
      expect(service.client).to be_a(Aws::S3::Client)
    end
  end

  describe '#upload_file' do
    let(:test_file_path) { Rails.root.join('spec', 'fixtures', 'test_document.txt') }

    before do
      # Create test file
      FileUtils.mkdir_p(File.dirname(test_file_path))
      File.write(test_file_path, "This is a test document for S3 upload.")
    end

    after do
      File.delete(test_file_path) if File.exist?(test_file_path)
    end

    it 'successfully uploads a file to S3' do
      result = service.upload_file(
        file_path: test_file_path.to_s,
        bucket: test_bucket,
        key: 'uploads/test.txt'
      )

      expect(result).to be_success

      result.value! => { success:, etag:, bucket:, key: }

      expect(success).to be true
      expect(etag).to be_present
      expect(bucket).to eq(test_bucket)
      expect(key).to eq('uploads/test.txt')

      # Verify file exists in LocalStack
      head_response = localstack_client.head_object(bucket: test_bucket, key: 'uploads/test.txt')
      expect(head_response).to be_present
    end

    it 'uploads file with metadata' do
      result = service.upload_file(
        file_path: test_file_path.to_s,
        bucket: test_bucket,
        key: 'uploads/test-with-metadata.txt',
        metadata: { 'learner-id' => '123', 'topic' => 'python' }
      )

      expect(result).to be_success

      # Verify metadata in S3
      head_response = localstack_client.head_object(bucket: test_bucket, key: 'uploads/test-with-metadata.txt')
      expect(head_response.metadata['learner-id']).to eq('123')
      expect(head_response.metadata['topic']).to eq('python')
    end

    it 'returns failure when file does not exist' do
      result = service.upload_file(
        file_path: '/nonexistent/file.txt',
        bucket: test_bucket,
        key: 'uploads/missing.txt'
      )

      expect(result).to be_failure
      expect(result.failure).to include('File not found')
    end

    it 'returns failure with invalid bucket name' do
      result = service.upload_file(
        file_path: test_file_path.to_s,
        bucket: 'Invalid Bucket Name!',
        key: 'uploads/test.txt'
      )

      expect(result).to be_failure
      expect(result.failure).to include('Invalid bucket name')
    end
  end

  describe '#download_file' do
    let(:test_content) { 'This is test content for download.' }
    let(:s3_key) { 'downloads/test-file.txt' }

    before do
      # Upload test file to S3
      localstack_client.put_object(
        bucket: test_bucket,
        key: s3_key,
        body: test_content
      )
    end

    it 'successfully downloads a file from S3' do
      download_path = Rails.root.join('tmp', 'downloaded-test.txt')

      result = service.download_file(
        bucket: test_bucket,
        key: s3_key,
        file_path: download_path.to_s
      )

      expect(result).to be_success

      result.value! => { success:, file_path:, size: }

      expect(success).to be true
      expect(File.exist?(file_path)).to be true
      expect(File.read(file_path)).to eq(test_content)
      expect(size).to eq(test_content.bytesize)

      # Cleanup
      File.delete(download_path) if File.exist?(download_path)
    end

    it 'returns failure when file does not exist in S3' do
      result = service.download_file(
        bucket: test_bucket,
        key: 'nonexistent/file.txt',
        file_path: Rails.root.join('tmp', 'missing.txt').to_s
      )

      expect(result).to be_failure
      expect(result.failure).to include('File not found in S3')
    end
  end

  describe '#list_files' do
    before do
      # Upload multiple test files
      %w[file1.txt file2.txt file3.txt].each do |filename|
        localstack_client.put_object(
          bucket: test_bucket,
          key: "documents/#{filename}",
          body: "Content of #{filename}"
        )
      end

      # Upload file in different prefix
      localstack_client.put_object(
        bucket: test_bucket,
        key: 'backups/backup1.txt',
        body: 'Backup content'
      )
    end

    it 'lists all files in bucket' do
      result = service.list_files(bucket: test_bucket)

      expect(result).to be_success

      result.value! => { success:, files:, count: }

      expect(success).to be true
      expect(count).to eq(4)
      expect(files.map { |f| f[:key] }).to contain_exactly(
        'documents/file1.txt',
        'documents/file2.txt',
        'documents/file3.txt',
        'backups/backup1.txt'
      )
    end

    it 'lists files with prefix filter' do
      result = service.list_files(
        bucket: test_bucket,
        prefix: 'documents/'
      )

      expect(result).to be_success

      result.value! => { files:, count: }

      expect(count).to eq(3)
      expect(files.map { |f| f[:key] }).to all(start_with('documents/'))
    end

    it 'returns empty array for non-existent prefix' do
      result = service.list_files(
        bucket: test_bucket,
        prefix: 'nonexistent/'
      )

      expect(result).to be_success

      result.value! => { files:, count: }

      expect(count).to eq(0)
      expect(files).to be_empty
    end
  end

  describe '#delete_file' do
    let(:s3_key) { 'temp/file-to-delete.txt' }

    before do
      # Upload test file
      localstack_client.put_object(
        bucket: test_bucket,
        key: s3_key,
        body: 'Temporary file'
      )
    end

    it 'successfully deletes a file from S3' do
      # Verify file exists
      expect do
        localstack_client.head_object(bucket: test_bucket, key: s3_key)
      end.not_to raise_error

      # Delete file
      result = service.delete_file(bucket: test_bucket, key: s3_key)

      expect(result).to be_success

      # Verify file no longer exists
      expect do
        localstack_client.head_object(bucket: test_bucket, key: s3_key)
      end.to raise_error(Aws::S3::Errors::NotFound)
    end

    it 'succeeds even when file does not exist (idempotent)' do
      result = service.delete_file(
        bucket: test_bucket,
        key: 'nonexistent/file.txt'
      )

      expect(result).to be_success
    end
  end

  describe '#file_exists?' do
    let(:existing_key) { 'exists/file.txt' }

    before do
      localstack_client.put_object(
        bucket: test_bucket,
        key: existing_key,
        body: 'File content'
      )
    end

    it 'returns true when file exists' do
      exists = service.file_exists?(bucket: test_bucket, key: existing_key)
      expect(exists).to be true
    end

    it 'returns false when file does not exist' do
      exists = service.file_exists?(bucket: test_bucket, key: 'nonexistent.txt')
      expect(exists).to be false
    end
  end

  describe '#get_presigned_url' do
    let(:s3_key) { 'shared/document.txt' }
    let(:test_content) { 'Shared document content' }

    before do
      localstack_client.put_object(
        bucket: test_bucket,
        key: s3_key,
        body: test_content
      )
    end

    it 'generates a presigned URL for file access' do
      result = service.get_presigned_url(
        bucket: test_bucket,
        key: s3_key,
        expiration: 3600
      )

      expect(result).to be_success

      result.value! => { success:, url:, expires_in: }

      expect(success).to be true
      expect(url).to be_present
      expect(url).to include(s3_key)
      expect(expires_in).to eq(3600)

      # Verify URL works (download content via HTTP)
      uri = URI.parse(url)
      response = Net::HTTP.get_response(uri)
      expect(response.code).to eq('200')
      expect(response.body).to eq(test_content)
    end

    it 'respects custom expiration time' do
      result = service.get_presigned_url(
        bucket: test_bucket,
        key: s3_key,
        expiration: 7200
      )

      expect(result).to be_success
      expect(result.value![:expires_in]).to eq(7200)
    end
  end

  describe '#batch_upload' do
    let(:files_to_upload) do
      [
        { file_path: Rails.root.join('tmp', 'batch1.txt').to_s, key: 'batch/file1.txt' },
        { file_path: Rails.root.join('tmp', 'batch2.txt').to_s, key: 'batch/file2.txt' },
        { file_path: Rails.root.join('tmp', 'batch3.txt').to_s, key: 'batch/file3.txt' }
      ]
    end

    before do
      # Create test files
      files_to_upload.each do |file|
        File.write(file[:file_path], "Content of #{file[:key]}")
      end
    end

    after do
      # Cleanup test files
      files_to_upload.each do |file|
        File.delete(file[:file_path]) if File.exist?(file[:file_path])
      end
    end

    it 'uploads multiple files successfully' do
      result = service.batch_upload(
        files: files_to_upload,
        bucket: test_bucket
      )

      expect(result).to be_success

      result.value! => { success:, uploaded_count:, failed_count:, uploaded: }

      expect(success).to be true
      expect(uploaded_count).to eq(3)
      expect(failed_count).to eq(0)
      expect(uploaded.size).to eq(3)

      # Verify all files in S3
      files_to_upload.each do |file|
        head_response = localstack_client.head_object(bucket: test_bucket, key: file[:key])
        expect(head_response).to be_present
      end
    end

    it 'reports failures for missing files' do
      files = files_to_upload + [
        { file_path: '/nonexistent/file.txt', key: 'batch/missing.txt' }
      ]

      result = service.batch_upload(files: files, bucket: test_bucket)

      expect(result).to be_success

      result.value! => { uploaded_count:, failed_count:, failed: }

      expect(uploaded_count).to eq(3)
      expect(failed_count).to eq(1)
      expect(failed.first[:file_path]).to eq('/nonexistent/file.txt')
    end
  end
end
