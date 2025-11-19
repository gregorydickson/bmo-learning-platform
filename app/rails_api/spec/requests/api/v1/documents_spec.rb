# frozen_string_literal: true

require 'rails_helper'
require 'webmock/rspec'

RSpec.describe 'Api::V1::Documents', type: :request do
  let(:headers) { { 'Content-Type' => 'application/json', 'Accept' => 'application/json' } }
  let(:test_bucket) { 'bmo-learning-test-documents' }

  # Mock S3 client
  let(:s3_client) do
    instance_double(
      Aws::S3::Client,
      put_object: double(etag: '"test-etag"'),
      head_object: double(etag: '"test-etag"', content_length: 1024, version_id: 'v1'),
      delete_object: true,
      presigned_url: 'https://s3.amazonaws.com/presigned-url'
    )
  end

  before do
    # Mock S3Service to avoid actual S3 calls
    allow_any_instance_of(S3Service).to receive(:client).and_return(s3_client)
    ENV['S3_DOCUMENTS_BUCKET'] = test_bucket
  end

  describe 'POST /api/v1/documents' do
    let(:upload_file) do
      fixture_file_upload(
        Rails.root.join('spec', 'fixtures', 'test_document.pdf'),
        'application/pdf'
      )
    end

    before do
      # Create fixture directory and file
      FileUtils.mkdir_p(Rails.root.join('spec', 'fixtures'))
      File.write(
        Rails.root.join('spec', 'fixtures', 'test_document.pdf'),
        'Fake PDF content for testing'
      )
    end

    after do
      File.delete(Rails.root.join('spec', 'fixtures', 'test_document.pdf')) rescue nil
    end

    context 'when upload succeeds' do
      it 'uploads document to S3 and creates database record' do
        post '/api/v1/documents', params: { file: upload_file }

        expect(response).to have_http_status(:created)

        json = JSON.parse(response.body)
        expect(json['success']).to be true
        expect(json['document']['filename']).to eq('test_document.pdf')
        expect(json['document']['s3_key']).to match(/uploads\/\d{4}-\d{2}-\d{2}\/.*test_document\.pdf/)
        expect(json['document']['size']).to be_present
        expect(json['document']['content_type']).to eq('application/pdf')
        expect(json['message']).to eq('Document uploaded successfully')

        # Verify document created in database
        document = Document.find(json['document']['id'])
        expect(document.filename).to eq('test_document.pdf')
        expect(document.s3_bucket).to eq(test_bucket)
        expect(document.processed).to be false
      end

      it 'uploads with metadata' do
        post '/api/v1/documents', params: {
          file: upload_file,
          category: 'lesson',
          learner_id: 123
        }

        expect(response).to have_http_status(:created)

        json = JSON.parse(response.body)
        document = Document.find(json['document']['id'])

        expect(document.category).to eq('lesson')
        expect(document.learner_id).to eq(123)
      end

      it 'triggers async processing when process_now=true' do
        allow(DocumentProcessingJob).to receive(:perform_async).and_return('job-123')

        post '/api/v1/documents', params: {
          file: upload_file,
          process_now: 'true'
        }

        expect(response).to have_http_status(:created)

        json = JSON.parse(response.body)
        expect(json['processing_job_id']).to eq('job-123')
        expect(json['message']).to eq('Document uploaded and processing started')

        expect(DocumentProcessingJob).to have_received(:perform_async)
      end

      it 'does not trigger processing when process_now is omitted' do
        allow(DocumentProcessingJob).to receive(:perform_async)

        post '/api/v1/documents', params: { file: upload_file }

        expect(DocumentProcessingJob).not_to have_received(:perform_async)
      end
    end

    context 'when upload fails' do
      it 'returns error when file is missing' do
        post '/api/v1/documents'

        expect(response).to have_http_status(:bad_request)

        json = JSON.parse(response.body)
        expect(json['success']).to be false
        expect(json['error']).to eq('No file provided')
      end

      it 'returns error when S3 upload fails' do
        allow_any_instance_of(S3Service).to receive(:upload_file)
          .and_return(Dry::Monads::Failure('S3 upload failed: Permission denied'))

        post '/api/v1/documents', params: { file: upload_file }

        expect(response).to have_http_status(:unprocessable_entity)

        json = JSON.parse(response.body)
        expect(json['success']).to be false
        expect(json['error']).to include('S3 upload failed')
      end
    end
  end

  describe 'GET /api/v1/documents' do
    let!(:documents) do
      [
        Document.create!(
          filename: 'doc1.pdf',
          s3_bucket: test_bucket,
          s3_key: 'uploads/doc1.pdf',
          size: 1024,
          content_type: 'application/pdf',
          category: 'lesson',
          learner_id: 1
        ),
        Document.create!(
          filename: 'doc2.txt',
          s3_bucket: test_bucket,
          s3_key: 'uploads/doc2.txt',
          size: 512,
          content_type: 'text/plain',
          category: 'reference',
          learner_id: 2
        ),
        Document.create!(
          filename: 'doc3.pdf',
          s3_bucket: test_bucket,
          s3_key: 'uploads/doc3.pdf',
          size: 2048,
          content_type: 'application/pdf',
          category: 'lesson',
          learner_id: 1
        )
      ]
    end

    it 'lists all documents' do
      get '/api/v1/documents', headers: headers

      expect(response).to have_http_status(:ok)

      json = JSON.parse(response.body)
      expect(json['success']).to be true
      expect(json['documents'].size).to eq(3)
      expect(json['pagination']['total_count']).to eq(3)
    end

    it 'filters by category' do
      get '/api/v1/documents', params: { category: 'lesson' }, headers: headers

      expect(response).to have_http_status(:ok)

      json = JSON.parse(response.body)
      expect(json['documents'].size).to eq(2)
      expect(json['documents'].map { |d| d['category'] }).to all(eq('lesson'))
    end

    it 'filters by learner_id' do
      get '/api/v1/documents', params: { learner_id: 1 }, headers: headers

      expect(response).to have_http_status(:ok)

      json = JSON.parse(response.body)
      expect(json['documents'].size).to eq(2)
      expect(json['documents'].map { |d| d['learner_id'] }).to all(eq(1))
    end

    it 'supports pagination' do
      get '/api/v1/documents', params: { page: 1, per_page: 2 }, headers: headers

      expect(response).to have_http_status(:ok)

      json = JSON.parse(response.body)
      expect(json['documents'].size).to eq(2)
      expect(json['pagination']['current_page']).to eq(1)
      expect(json['pagination']['total_pages']).to eq(2)
      expect(json['pagination']['per_page']).to eq(2)
    end

    it 'limits per_page to maximum of 100' do
      get '/api/v1/documents', params: { per_page: 200 }, headers: headers

      expect(response).to have_http_status(:ok)

      json = JSON.parse(response.body)
      expect(json['pagination']['per_page']).to eq(100)
    end
  end

  describe 'GET /api/v1/documents/:id' do
    let!(:document) do
      Document.create!(
        filename: 'test.pdf',
        s3_bucket: test_bucket,
        s3_key: 'uploads/test.pdf',
        size: 1024,
        content_type: 'application/pdf',
        category: 'lesson',
        processed: true,
        processed_at: 1.hour.ago
      )
    end

    it 'returns document details' do
      get "/api/v1/documents/#{document.id}", headers: headers

      expect(response).to have_http_status(:ok)

      json = JSON.parse(response.body)
      expect(json['success']).to be true
      expect(json['document']['id']).to eq(document.id)
      expect(json['document']['filename']).to eq('test.pdf')
      expect(json['document']['processed']).to be true
      expect(json['document']['processed_at']).to be_present
    end

    it 'returns 404 when document does not exist' do
      get '/api/v1/documents/999999', headers: headers

      expect(response).to have_http_status(:not_found)

      json = JSON.parse(response.body)
      expect(json['success']).to be false
      expect(json['error']).to eq('Document not found')
    end
  end

  describe 'DELETE /api/v1/documents/:id' do
    let!(:document) do
      Document.create!(
        filename: 'delete-me.pdf',
        s3_bucket: test_bucket,
        s3_key: 'uploads/delete-me.pdf',
        size: 1024,
        content_type: 'application/pdf'
      )
    end

    it 'deletes document from S3 and database' do
      delete "/api/v1/documents/#{document.id}", headers: headers

      expect(response).to have_http_status(:ok)

      json = JSON.parse(response.body)
      expect(json['success']).to be true
      expect(json['message']).to eq('Document deleted successfully')

      # Verify deleted from database
      expect(Document.exists?(document.id)).to be false

      # Verify S3 delete was called
      expect(s3_client).to have_received(:delete_object).with(
        bucket: test_bucket,
        key: 'uploads/delete-me.pdf'
      )
    end

    it 'returns error when S3 delete fails' do
      allow_any_instance_of(S3Service).to receive(:delete_file)
        .and_return(Dry::Monads::Failure('S3 delete failed'))

      delete "/api/v1/documents/#{document.id}", headers: headers

      expect(response).to have_http_status(:unprocessable_entity)

      json = JSON.parse(response.body)
      expect(json['success']).to be false

      # Verify document still exists in database
      expect(Document.exists?(document.id)).to be true
    end

    it 'returns 404 when document does not exist' do
      delete '/api/v1/documents/999999', headers: headers

      expect(response).to have_http_status(:not_found)
    end
  end

  describe 'GET /api/v1/documents/:id/download_url' do
    let!(:document) do
      Document.create!(
        filename: 'download-test.pdf',
        s3_bucket: test_bucket,
        s3_key: 'uploads/download-test.pdf',
        size: 1024,
        content_type: 'application/pdf'
      )
    end

    it 'generates presigned URL with default expiration' do
      get "/api/v1/documents/#{document.id}/download_url", headers: headers

      expect(response).to have_http_status(:ok)

      json = JSON.parse(response.body)
      expect(json['success']).to be true
      expect(json['url']).to be_present
      expect(json['expires_in']).to eq(3600) # Default 1 hour
      expect(json['document']['id']).to eq(document.id)
      expect(json['document']['filename']).to eq('download-test.pdf')
    end

    it 'generates presigned URL with custom expiration' do
      get "/api/v1/documents/#{document.id}/download_url",
          params: { expires_in: 7200 },
          headers: headers

      expect(response).to have_http_status(:ok)

      json = JSON.parse(response.body)
      expect(json['expires_in']).to eq(7200) # 2 hours
    end

    it 'limits expiration to maximum of 24 hours' do
      get "/api/v1/documents/#{document.id}/download_url",
          params: { expires_in: 100_000 },
          headers: headers

      expect(response).to have_http_status(:ok)

      json = JSON.parse(response.body)
      expect(json['expires_in']).to eq(86_400) # 24 hours max
    end

    it 'returns 404 when document does not exist' do
      get '/api/v1/documents/999999/download_url', headers: headers

      expect(response).to have_http_status(:not_found)
    end

    it 'returns error when presigned URL generation fails' do
      allow_any_instance_of(S3Service).to receive(:get_presigned_url)
        .and_return(Dry::Monads::Failure('Failed to generate URL'))

      get "/api/v1/documents/#{document.id}/download_url", headers: headers

      expect(response).to have_http_status(:unprocessable_entity)

      json = JSON.parse(response.body)
      expect(json['success']).to be false
    end
  end
end
