# frozen_string_literal: true

require 'httparty'

##
# DocumentProcessingJob - Async job for processing uploaded documents via AI service
#
# This job is enqueued when a document is uploaded with process_now=true.
# It calls the Python AI service to:
# - Extract text from the document (PDF, TXT, etc.)
# - Chunk the content for RAG
# - Generate embeddings
# - Store in vector database (Chroma)
#
# Sidekiq Configuration:
# - Queue: ai_processing (dedicated queue for AI operations)
# - Retry: 3 attempts with exponential backoff
# - Dead: true (failed jobs go to dead queue for manual review)
#
# Usage:
#   DocumentProcessingJob.perform_async(document.id)
#
class DocumentProcessingJob
  include Sidekiq::Job

  # Sidekiq configuration
  sidekiq_options queue: 'ai_processing', retry: 3, dead: true

  ##
  # Process a document by calling the AI service
  #
  # @param document_id [Integer] ID of the Document record
  # @raise [ActiveRecord::RecordNotFound] If document doesn't exist
  # @raise [StandardError] If AI service call fails (triggers Sidekiq retry)
  #
  def perform(document_id)
    document = Document.find(document_id)

    Rails.logger.info(
      '[DocumentProcessingJob] Starting document processing',
      document_id: document.id,
      filename: document.filename,
      s3_uri: document.s3_uri
    )

    # Call AI service to process document
    response = call_ai_service(document)

    # Handle response
    if response.success?
      handle_success(document, response)
    else
      handle_error(document, response)
    end
  rescue ActiveRecord::RecordNotFound => e
    Rails.logger.error(
      '[DocumentProcessingJob] Document not found',
      document_id: document_id,
      error: e.message
    )
    raise # Re-raise to mark job as failed
  rescue StandardError => e
    Rails.logger.error(
      '[DocumentProcessingJob] Unexpected error',
      document_id: document_id,
      error: e.message,
      backtrace: e.backtrace.first(5)
    )
    # Mark document as failed before re-raising
    document&.mark_failed!("Unexpected error: #{e.message}")
    raise # Re-raise to trigger Sidekiq retry
  end

  private

  ##
  # Call Python AI service to process document
  #
  # @param document [Document] Document to process
  # @return [HTTParty::Response] API response
  #
  def call_ai_service(document)
    ai_service_url = ENV.fetch('AI_SERVICE_URL', 'http://localhost:8000')
    endpoint = "#{ai_service_url}/api/v1/process-document"

    request_body = {
      document_id: document.id,
      s3_bucket: document.s3_bucket,
      s3_key: document.s3_key,
      content_type: document.content_type,
      filename: document.filename,
      category: document.category
    }

    # Include metadata if present
    request_body[:metadata] = document.metadata if document.metadata.present?

    Rails.logger.debug(
      '[DocumentProcessingJob] Calling AI service',
      endpoint: endpoint,
      document_id: document.id
    )

    response = HTTParty.post(
      endpoint,
      body: request_body.to_json,
      headers: {
        'Content-Type' => 'application/json',
        'Accept' => 'application/json'
      },
      timeout: 300 # 5 minutes for large documents
    )

    response
  rescue Net::OpenTimeout, Net::ReadTimeout => e
    Rails.logger.error(
      '[DocumentProcessingJob] AI service timeout',
      document_id: document.id,
      error: e.message
    )
    document.mark_failed!("Connection timeout: #{e.message}")
    raise StandardError, "AI service unavailable: Connection timeout"
  rescue SocketError, Errno::ECONNREFUSED => e
    Rails.logger.error(
      '[DocumentProcessingJob] AI service connection failed',
      document_id: document.id,
      error: e.message
    )
    document.mark_failed!("Connection failed: #{e.message}")
    raise StandardError, "AI service unavailable: #{e.message}"
  end

  ##
  # Handle successful AI service response
  #
  # @param document [Document] Document being processed
  # @param response [HTTParty::Response] Successful API response
  #
  def handle_success(document, response)
    begin
      result = JSON.parse(response.body)
    rescue JSON::ParserError => e
      Rails.logger.error(
        '[DocumentProcessingJob] Invalid JSON response',
        document_id: document.id,
        response_body: response.body,
        error: e.message
      )
      document.mark_failed!("JSON parse error: #{e.message}")
      raise StandardError, "Failed to parse AI service response: #{e.message}"
    end

    if result['success']
      document.mark_processed!

      Rails.logger.info(
        '[DocumentProcessingJob] Document processed successfully',
        document_id: document.id,
        chunks_created: result['chunks_created'],
        embeddings_created: result['embeddings_created'],
        processing_time: result['processing_time_seconds']
      )
    else
      # AI service returned success: false
      error_message = result['error'] || 'Unknown error from AI service'

      Rails.logger.error(
        '[DocumentProcessingJob] AI service processing failed',
        document_id: document.id,
        error: error_message
      )

      document.mark_failed!(error_message)
      raise StandardError, "AI service processing failed: #{error_message}"
    end
  end

  ##
  # Handle error response from AI service
  #
  # @param document [Document] Document being processed
  # @param response [HTTParty::Response] Error API response
  #
  def handle_error(document, response)
    begin
      result = JSON.parse(response.body)
      error_message = result['error'] || "HTTP #{response.code}: #{response.message}"
    rescue JSON::ParserError
      error_message = "HTTP #{response.code}: #{response.body}"
    end

    Rails.logger.error(
      '[DocumentProcessingJob] AI service returned error',
      document_id: document.id,
      status_code: response.code,
      error: error_message
    )

    document.mark_failed!(error_message)

    # Re-raise to trigger Sidekiq retry for 5xx errors (server issues)
    # Don't retry for 4xx errors (client errors - bad request, invalid file, etc.)
    if response.code >= 500
      raise StandardError, "AI service error (retryable): #{error_message}"
    else
      # 4xx error - don't retry, just fail the job
      Rails.logger.warn(
        '[DocumentProcessingJob] Client error - not retrying',
        document_id: document.id,
        status_code: response.code
      )
    end
  end
end
