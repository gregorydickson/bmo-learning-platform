# frozen_string_literal: true

require 'httparty'

class AiServiceClient
  include HTTParty
  base_uri ENV.fetch('AI_SERVICE_URL', 'http://localhost:8000')

  def generate_lesson(topic:, learner_id: nil)
    response = self.class.post(
      '/api/v1/generate-lesson',
      body: {
        topic: topic,
        learner_id: learner_id
      }.to_json,
      headers: { 'Content-Type' => 'application/json' }
    )

    handle_response(response)
  end

  def validate_safety(content:)
    response = self.class.post(
      '/api/v1/validate-safety',
      body: { content: content }.to_json,
      headers: { 'Content-Type' => 'application/json' }
    )

    handle_response(response)
  end

  private

  def handle_response(response)
    if response.success?
      JSON.parse(response.body, symbolize_names: true)
    else
      raise "AI Service error: #{response.code} - #{response.message}"
    end
  end
end
