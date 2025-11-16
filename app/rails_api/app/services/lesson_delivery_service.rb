# frozen_string_literal: true

class LessonDeliveryService
  attr_reader :learning_path

  def initialize(learning_path)
    @learning_path = learning_path
    @ai_client = AiServiceClient.new
  end

  def generate_and_deliver_lesson(channel: 'email')
    # Generate lesson via AI service
    ai_response = @ai_client.generate_lesson(
      topic: learning_path.topic,
      learner_id: learning_path.learner_id.to_s
    )

    # Create lesson record
    lesson = create_lesson(ai_response[:lesson])

    # Deliver via selected channel
    deliver_lesson(lesson, channel)

    lesson
  end

  private

  def create_lesson(lesson_data)
    learning_path.lessons.create!(
      topic: lesson_data[:topic],
      content: lesson_data[:content],
      key_points: lesson_data[:key_points],
      scenario: lesson_data[:scenario],
      quiz_question: lesson_data[:quiz_question],
      quiz_options: lesson_data[:quiz_options],
      correct_answer: lesson_data[:correct_answer]
    )
  end

  def deliver_lesson(lesson, channel)
    case channel
    when 'slack'
      deliver_via_slack(lesson)
    when 'sms'
      deliver_via_sms(lesson)
    else
      deliver_via_email(lesson)
    end

    lesson.mark_delivered!(channel: channel)
  end

  def deliver_via_email(lesson)
    # Email delivery logic
    Rails.logger.info "Delivering lesson #{lesson.id} via email"
  end

  def deliver_via_slack(lesson)
    # Slack delivery logic
    Rails.logger.info "Delivering lesson #{lesson.id} via Slack"
  end

  def deliver_via_sms(lesson)
    # SMS delivery logic
    Rails.logger.info "Delivering lesson #{lesson.id} via SMS"
  end
end
