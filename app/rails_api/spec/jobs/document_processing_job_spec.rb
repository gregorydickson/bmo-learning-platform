# frozen_string_literal: true

require 'rails_helper'
require 'webmock/rspec'

RSpec.describe DocumentProcessingJob, type: :job do
  let(:document) do
    Document.create!(
      filename: 'python-tutorial.pdf',
      s3_bucket: 'bmo-learning-test-documents',
      s3_key: 'uploads/2025-11-18/python-tutorial.pdf',
      s3_etag: '"abc123"',
      size: 1024000,
      content_type: 'application/pdf',
      category: 'lesson',
      learner_id: 1,
      processed: false
    )
  end

  let(:ai_service_url) { ENV.fetch('AI_SERVICE_URL', 'http://localhost:8000') }
  let(:processing_endpoint) { "#{ai_service_url}/api/v1/process-document" }

  before do
    # Mock AI service responses
    stub_request(:post, processing_endpoint)
      .to_return(status: 200, body: success_response.to_json, headers: { 'Content-Type' => 'application/json' })
  end

  let(:success_response) do
    {
      success: true,
      document_id: document.id,
      s3_uri: document.s3_uri,
      chunks_created: 25,
      embeddings_created: 25,
      processing_time_seconds: 12.5
    }
  end

  describe '#perform' do
    context 'when document processing succeeds' do
      it 'calls AI service with document details' do
        DocumentProcessingJob.new.perform(document.id)

        expect(WebMock).to have_requested(:post, processing_endpoint)
          .with(
            body: hash_including(
              document_id: document.id,
              s3_bucket: document.s3_bucket,
              s3_key: document.s3_key,
              content_type: document.content_type
            )
          ).once
      end

      it 'marks document as processed on success' do
        expect do
          DocumentProcessingJob.new.perform(document.id)
        end.to change { document.reload.processed? }.from(false).to(true)

        expect(document.processed_at).to be_present
        expect(document.processing_error).to be_nil
      end

      it 'logs processing success' do
        expect(Rails.logger).to receive(:info).with(
          '[DocumentProcessingJob] Starting document processing',
          hash_including(document_id: document.id)
        )

        expect(Rails.logger).to receive(:info).with(
          '[DocumentProcessingJob] Document processed successfully',
          hash_including(
            document_id: document.id,
            chunks_created: 25
          )
        )

        DocumentProcessingJob.new.perform(document.id)
      end

      it 'includes metadata in AI service request if present' do
        document.update!(metadata: { 'topic' => 'python', 'difficulty' => 'beginner' })

        DocumentProcessingJob.new.perform(document.id)

        expect(WebMock).to have_requested(:post, processing_endpoint)
          .with(
            body: hash_including(
              metadata: { 'topic' => 'python', 'difficulty' => 'beginner' }
            )
          ).once
      end
    end

    context 'when document does not exist' do
      it 'raises ActiveRecord::RecordNotFound' do
        expect do
          DocumentProcessingJob.new.perform(999_999)
        end.to raise_error(ActiveRecord::RecordNotFound)
      end
    end

    context 'when AI service returns error' do
      let(:error_response) do
        {
          success: false,
          error: 'Invalid file format: corrupted PDF'
        }
      end

      before do
        stub_request(:post, processing_endpoint)
          .to_return(status: 422, body: error_response.to_json, headers: { 'Content-Type' => 'application/json' })
      end

      it 'marks document as failed with error message' do
        expect do
          DocumentProcessingJob.new.perform(document.id)
        end.to raise_error(StandardError, /AI service processing failed/)

        document.reload
        expect(document.processed?).to be false
        expect(document.processed_at).to be_present
        expect(document.processing_error).to include('Invalid file format')
      end

      it 'logs the error' do
        expect(Rails.logger).to receive(:error).with(
          '[DocumentProcessingJob] AI service processing failed',
          hash_including(
            document_id: document.id,
            error: 'Invalid file format: corrupted PDF'
          )
        )

        expect do
          DocumentProcessingJob.new.perform(document.id)
        end.to raise_error(StandardError)
      end
    end

    context 'when AI service is unavailable' do
      before do
        stub_request(:post, processing_endpoint).to_timeout
      end

      it 'marks document as failed and raises error for retry' do
        expect do
          DocumentProcessingJob.new.perform(document.id)
        end.to raise_error(StandardError, /AI service unavailable/)

        document.reload
        expect(document.processed?).to be false
        expect(document.processing_error).to include('Connection timeout')
      end
    end

    context 'when AI service returns invalid JSON' do
      before do
        stub_request(:post, processing_endpoint)
          .to_return(status: 200, body: 'Invalid JSON{', headers: { 'Content-Type' => 'application/json' })
      end

      it 'marks document as failed with parse error' do
        expect do
          DocumentProcessingJob.new.perform(document.id)
        end.to raise_error(StandardError, /Failed to parse AI service response/)

        document.reload
        expect(document.processing_error).to include('JSON parse error')
      end
    end
  end

  describe 'Sidekiq configuration' do
    it 'is configured with correct queue' do
      expect(DocumentProcessingJob.sidekiq_options['queue']).to eq('ai_processing')
    end

    it 'is configured with retry policy' do
      expect(DocumentProcessingJob.sidekiq_options['retry']).to eq(3)
    end

    it 'is configured with dead flag' do
      expect(DocumentProcessingJob.sidekiq_options['dead']).to eq(true)
    end
  end

  describe 'retry behavior' do
    context 'when job fails with retryable error' do
      before do
        stub_request(:post, processing_endpoint).to_timeout
      end

      it 'allows Sidekiq to retry the job' do
        expect do
          DocumentProcessingJob.new.perform(document.id)
        end.to raise_error(StandardError)

        # Sidekiq will automatically retry based on retry policy
      end
    end
  end

  describe 'integration with DocumentsController' do
    it 'is enqueued when process_now=true in controller' do
      # This test verifies the integration point exists
      # Actual enqueuing tested in request specs

      expect(DocumentProcessingJob).to respond_to(:perform_async)
    end
  end
end
