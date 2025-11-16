# frozen_string_literal: true

class Lesson < ApplicationRecord
  belongs_to :learning_path
  has_many :quiz_responses, dependent: :destroy

  validates :topic, :content, presence: true

  scope :delivered, -> { where.not(delivered_at: nil) }
  scope :undelivered, -> { where(delivered_at: nil) }

  def delivered?
    delivered_at.present?
  end

  def mark_delivered!(channel:)
    update!(
      delivered_at: Time.current,
      delivery_channel: channel
    )
  end
end
