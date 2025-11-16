# frozen_string_literal: true

class QuizResponse < ApplicationRecord
  belongs_to :learner
  belongs_to :lesson

  validates :answer_given, presence: true
  validates :correct, inclusion: { in: [true, false] }

  after_create :update_learning_path_progress

  private

  def update_learning_path_progress
    return unless correct

    learning_path = lesson.learning_path
    learning_path.increment!(:lessons_completed)

    if learning_path.lessons_completed >= learning_path.total_lessons
      learning_path.complete!
    end
  end
end
