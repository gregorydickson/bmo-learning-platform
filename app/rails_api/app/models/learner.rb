# frozen_string_literal: true

class Learner < ApplicationRecord
  has_many :learning_paths, dependent: :destroy
  has_many :quiz_responses, dependent: :destroy

  validates :email, presence: true, uniqueness: true, format: { with: URI::MailTo::EMAIL_REGEXP }
  validates :name, presence: true

  def completion_rate
    total_lessons = learning_paths.sum(:total_lessons)
    return 0 if total_lessons.zero?

    completed = learning_paths.sum(:lessons_completed)
    (completed.to_f / total_lessons * 100).round(2)
  end

  def quiz_accuracy
    total = quiz_responses.count
    return 0 if total.zero?

    correct = quiz_responses.where(correct: true).count
    (correct.to_f / total * 100).round(2)
  end
end
