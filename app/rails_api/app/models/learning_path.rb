# frozen_string_literal: true

class LearningPath < ApplicationRecord
  belongs_to :learner
  has_many :lessons, dependent: :destroy

  validates :topic, presence: true
  validates :status, inclusion: { in: %w[active paused completed] }

  scope :active, -> { where(status: 'active') }
  scope :completed, -> { where(status: 'completed') }

  def progress_percentage
    return 0 if total_lessons.zero?
    (lessons_completed.to_f / total_lessons * 100).round(2)
  end

  def complete!
    update!(status: 'completed')
  end
end
