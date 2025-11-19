# frozen_string_literal: true

##
# Document - Represents uploaded documents stored in S3
#
# Attributes:
#   filename: Original filename
#   s3_bucket: S3 bucket name
#   s3_key: S3 object key (path in bucket)
#   s3_etag: S3 ETag for version tracking
#   size: File size in bytes
#   content_type: MIME type
#   category: Document category (lesson, reference, quiz, general)
#   learner_id: Associated learner (optional)
#   uploaded_by: User ID who uploaded
#   processed: Whether AI processing completed
#   processed_at: Timestamp of processing completion
#   processing_error: Error message if processing failed
#   metadata: Additional JSON metadata
#
class Document < ApplicationRecord
  # Associations
  belongs_to :learner, optional: true
  belongs_to :uploader, class_name: 'User', foreign_key: 'uploaded_by', optional: true

  # Validations
  validates :filename, presence: true
  validates :s3_bucket, presence: true
  validates :s3_key, presence: true, uniqueness: true
  validates :category, inclusion: { in: %w[lesson reference quiz general] }

  # Scopes
  scope :processed, -> { where(processed: true) }
  scope :pending, -> { where(processed: false) }
  scope :by_category, ->(category) { where(category: category) }
  scope :by_learner, ->(learner_id) { where(learner_id: learner_id) }
  scope :recent, -> { order(created_at: :desc) }

  ##
  # Check if document has been processed
  #
  # @return [Boolean]
  #
  def processed?
    processed == true
  end

  ##
  # Mark document as processed successfully
  #
  # @return [Boolean] True if saved successfully
  #
  def mark_processed!
    update!(
      processed: true,
      processed_at: Time.current,
      processing_error: nil
    )
  end

  ##
  # Mark document processing as failed
  #
  # @param error [String] Error message
  # @return [Boolean] True if saved successfully
  #
  def mark_failed!(error)
    update!(
      processed: false,
      processed_at: Time.current,
      processing_error: error
    )
  end

  ##
  # Get S3 URI for this document
  #
  # @return [String] S3 URI (s3://bucket/key)
  #
  def s3_uri
    "s3://#{s3_bucket}/#{s3_key}"
  end

  ##
  # Get human-readable file size
  #
  # @return [String] Formatted file size
  #
  def human_size
    return 'Unknown' if size.nil?

    units = %w[B KB MB GB TB]
    size_float = size.to_f
    unit_index = 0

    while size_float >= 1024 && unit_index < units.length - 1
      size_float /= 1024.0
      unit_index += 1
    end

    format('%.2f %s', size_float, units[unit_index])
  end
end
