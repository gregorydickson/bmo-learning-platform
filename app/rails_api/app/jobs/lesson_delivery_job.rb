# frozen_string_literal: true

class LessonDeliveryJob < ApplicationJob
  queue_as :default

  def perform(learning_path_id, channel: 'email')
    learning_path = LearningPath.find(learning_path_id)
    service = LessonDeliveryService.new(learning_path)

    service.generate_and_deliver_lesson(channel: channel)
  end
end
