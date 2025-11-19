# frozen_string_literal: true

module Api
  module V1
    ##
    # DocumentsController - Handle document uploads and processing
    #
    # Endpoints:
    #   POST /api/v1/documents - Upload a document to S3
    #   GET /api/v1/documents/:id - Get document metadata
    #   DELETE /api/v1/documents/:id - Delete a document
    #   GET /api/v1/documents - List documents
    #
    class DocumentsController < ApplicationController
      before_action :authenticate_user!, except: [:index]
      before_action :set_document, only: [:show, :destroy, :download_url]

      ##
      # POST /api/v1/documents
      #
      # Upload a document to S3 and optionally trigger AI processing
      #
      # Parameters:
      #   - file: uploaded file (required)
      #   - learner_id: ID of learner (optional)
      #   - category: document category (optional: 'lesson', 'reference', 'quiz')
      #   - process_now: trigger immediate AI processing (optional, default: false)
      #
      # Response:
      #   {
      #     "success": true,
      #     "document": {
      #       "id": 123,
      #       "filename": "python-tutorial.pdf",
      #       "s3_key": "uploads/2025-11-18/python-tutorial.pdf",
      #       "size": 1024000,
      #       "content_type": "application/pdf",
      #       "uploaded_at": "2025-11-18T10:30:00Z"
      #     },
      #     "processing_job_id": "abc123" (if process_now=true)
      #   }
      #
      def create
        uploaded_file = params[:file]

        unless uploaded_file
          return render json: {
            success: false,
            error: 'No file provided'
          }, status: :bad_request
        end

        # Generate S3 key with date prefix for organization
        date_prefix = Time.current.strftime('%Y-%m-%d')
        s3_key = "uploads/#{date_prefix}/#{SecureRandom.uuid}-#{uploaded_file.original_filename}"
        bucket = ENV.fetch('S3_DOCUMENTS_BUCKET', 'bmo-learning-test-documents')

        # Upload to S3
        s3_service = S3Service.new
        result = s3_service.upload_file(
          file_path: uploaded_file.tempfile.path,
          bucket: bucket,
          key: s3_key,
          content_type: uploaded_file.content_type,
          metadata: {
            'original-filename' => uploaded_file.original_filename,
            'uploaded-by' => current_user&.id&.to_s || 'anonymous',
            'category' => params[:category] || 'general'
          }
        )

        case result
        in Success(upload_data)
          # Create document record
          document = Document.create!(
            filename: uploaded_file.original_filename,
            s3_bucket: bucket,
            s3_key: s3_key,
            s3_etag: upload_data[:etag],
            size: upload_data[:size],
            content_type: uploaded_file.content_type,
            category: params[:category] || 'general',
            learner_id: params[:learner_id],
            uploaded_by: current_user&.id
          )

          response_data = {
            success: true,
            document: {
              id: document.id,
              filename: document.filename,
              s3_key: document.s3_key,
              size: document.size,
              content_type: document.content_type,
              category: document.category,
              uploaded_at: document.created_at
            }
          }

          # Optionally trigger AI processing
          if params[:process_now] == 'true'
            job_id = DocumentProcessingJob.perform_async(document.id)
            response_data[:processing_job_id] = job_id
            response_data[:message] = 'Document uploaded and processing started'
          else
            response_data[:message] = 'Document uploaded successfully'
          end

          render json: response_data, status: :created

        in Failure(error)
          Rails.logger.error(
            "[DocumentsController] Upload failed",
            error: error,
            filename: uploaded_file.original_filename
          )

          render json: {
            success: false,
            error: error
          }, status: :unprocessable_entity
        end
      rescue StandardError => e
        Rails.logger.error(
          "[DocumentsController] Unexpected error",
          error: e.message,
          backtrace: e.backtrace.first(5)
        )

        render json: {
          success: false,
          error: 'Internal server error'
        }, status: :internal_server_error
      end

      ##
      # GET /api/v1/documents
      #
      # List documents with optional filtering
      #
      # Parameters:
      #   - category: filter by category
      #   - learner_id: filter by learner
      #   - page: page number (default: 1)
      #   - per_page: results per page (default: 20, max: 100)
      #
      def index
        documents = Document.all

        # Apply filters
        documents = documents.where(category: params[:category]) if params[:category].present?
        documents = documents.where(learner_id: params[:learner_id]) if params[:learner_id].present?

        # Pagination
        page = params.fetch(:page, 1).to_i
        per_page = [params.fetch(:per_page, 20).to_i, 100].min

        documents = documents.page(page).per(per_page)

        render json: {
          success: true,
          documents: documents.map { |doc| document_json(doc) },
          pagination: {
            current_page: documents.current_page,
            total_pages: documents.total_pages,
            total_count: documents.total_count,
            per_page: per_page
          }
        }
      end

      ##
      # GET /api/v1/documents/:id
      #
      # Get document metadata
      #
      def show
        render json: {
          success: true,
          document: document_json(@document)
        }
      end

      ##
      # DELETE /api/v1/documents/:id
      #
      # Delete document from S3 and database
      #
      def destroy
        s3_service = S3Service.new

        # Delete from S3
        result = s3_service.delete_file(
          bucket: @document.s3_bucket,
          key: @document.s3_key
        )

        case result
        in Success(_)
          @document.destroy

          render json: {
            success: true,
            message: 'Document deleted successfully'
          }

        in Failure(error)
          render json: {
            success: false,
            error: error
          }, status: :unprocessable_entity
        end
      end

      ##
      # GET /api/v1/documents/:id/download_url
      #
      # Generate a presigned URL for downloading the document
      #
      # Parameters:
      #   - expires_in: URL expiration in seconds (default: 3600 = 1 hour, max: 86400 = 24 hours)
      #
      def download_url
        expires_in = [params.fetch(:expires_in, 3600).to_i, 86_400].min

        s3_service = S3Service.new
        result = s3_service.get_presigned_url(
          bucket: @document.s3_bucket,
          key: @document.s3_key,
          expiration: expires_in
        )

        case result
        in Success(data)
          render json: {
            success: true,
            url: data[:url],
            expires_in: data[:expires_in],
            document: {
              id: @document.id,
              filename: @document.filename
            }
          }

        in Failure(error)
          render json: {
            success: false,
            error: error
          }, status: :unprocessable_entity
        end
      end

      private

      def set_document
        @document = Document.find(params[:id])
      rescue ActiveRecord::RecordNotFound
        render json: {
          success: false,
          error: 'Document not found'
        }, status: :not_found
      end

      def document_json(document)
        {
          id: document.id,
          filename: document.filename,
          s3_key: document.s3_key,
          size: document.size,
          content_type: document.content_type,
          category: document.category,
          learner_id: document.learner_id,
          uploaded_at: document.created_at,
          processed: document.processed?,
          processed_at: document.processed_at
        }
      end
    end
  end
end
