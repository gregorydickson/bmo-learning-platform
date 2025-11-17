# frozen_string_literal: true

require 'rails_helper'

RSpec.describe AiServiceClient do
  let(:client) { described_class.new }
  let(:ai_service_url) { ENV.fetch('AI_SERVICE_URL', 'http://localhost:8000') }

  describe '#generate_lesson' do
    let(:topic) { 'Python Functions' }
    let(:learner_id) { '123' }

    context 'when AI service responds successfully' do
      let(:success_response) do
        {
          lesson: {
            topic: 'Python Functions',
            content: 'Functions are reusable blocks of code...',
            scenario: 'Building a calculator app...',
            quiz_question: 'What keyword defines a function?',
            quiz_options: ['func', 'def', 'function', 'define'],
            quiz_answer: 'def'
          },
          metadata: {
            generated_at: '2025-11-16T00:00:00Z',
            model: 'gpt-4-turbo-preview'
          },
          safety_check: {
            passed: true,
            pii_detected: false,
            moderation_flagged: false,
            issues: []
          }
        }
      end

      before do
        stub_request(:post, "#{ai_service_url}/api/v1/generate-lesson")
          .with(
            body: { topic: topic, learner_id: learner_id }.to_json,
            headers: { 'Content-Type' => 'application/json' }
          )
          .to_return(
            status: 200,
            body: success_response.to_json,
            headers: { 'Content-Type' => 'application/json' }
          )
      end

      it 'returns parsed response with symbolized keys' do
        result = client.generate_lesson(topic: topic, learner_id: learner_id)

        expect(result).to be_a(Hash)
        expect(result[:lesson]).to be_present
        expect(result[:lesson][:topic]).to eq('Python Functions')
        expect(result[:metadata]).to be_present
        expect(result[:safety_check]).to be_present
      end

      it 'sends correct request payload' do
        client.generate_lesson(topic: topic, learner_id: learner_id)

        expect(WebMock).to have_requested(:post, "#{ai_service_url}/api/v1/generate-lesson")
          .with(
            body: { topic: topic, learner_id: learner_id }.to_json,
            headers: { 'Content-Type' => 'application/json' }
          ).once
      end
    end

    context 'when AI service returns error' do
      before do
        stub_request(:post, "#{ai_service_url}/api/v1/generate-lesson")
          .to_return(status: 500, body: 'Internal Server Error')
      end

      it 'raises an error with status code and message' do
        expect {
          client.generate_lesson(topic: topic, learner_id: learner_id)
        }.to raise_error(/AI Service error: 500/)
      end
    end

    context 'when AI service is unreachable' do
      before do
        stub_request(:post, "#{ai_service_url}/api/v1/generate-lesson")
          .to_timeout
      end

      it 'raises a connection error' do
        expect {
          client.generate_lesson(topic: topic, learner_id: learner_id)
        }.to raise_error(Net::OpenTimeout)
      end
    end

    context 'when learner_id is not provided' do
      before do
        stub_request(:post, "#{ai_service_url}/api/v1/generate-lesson")
          .with(
            body: { topic: topic, learner_id: nil }.to_json
          )
          .to_return(
            status: 200,
            body: success_response.to_json
          )
      end

      let(:success_response) do
        {
          lesson: { topic: topic, content: 'Content' },
          metadata: {},
          safety_check: { passed: true }
        }
      end

      it 'sends request without learner_id' do
        client.generate_lesson(topic: topic)

        expect(WebMock).to have_requested(:post, "#{ai_service_url}/api/v1/generate-lesson")
          .with(body: hash_including(learner_id: nil))
      end
    end

    context 'when AI service returns invalid JSON' do
      before do
        stub_request(:post, "#{ai_service_url}/api/v1/generate-lesson")
          .to_return(
            status: 200,
            body: 'invalid json'
          )
      end

      it 'raises JSON parse error' do
        expect {
          client.generate_lesson(topic: topic)
        }.to raise_error(JSON::ParserError)
      end
    end

    context 'when AI service returns 4xx error' do
      before do
        stub_request(:post, "#{ai_service_url}/api/v1/generate-lesson")
          .to_return(status: 422, body: { error: 'Validation failed' }.to_json)
      end

      it 'raises an error' do
        expect {
          client.generate_lesson(topic: topic)
        }.to raise_error(/AI Service error: 422/)
      end
    end
  end

  describe '#validate_safety' do
    let(:content) { 'This is test content' }

    context 'when content is safe' do
      let(:safe_response) do
        {
          passed: true,
          pii_detected: false,
          moderation_flagged: false,
          issues: []
        }
      end

      before do
        stub_request(:post, "#{ai_service_url}/api/v1/validate-safety")
          .with(
            body: { content: content }.to_json,
            headers: { 'Content-Type' => 'application/json' }
          )
          .to_return(
            status: 200,
            body: safe_response.to_json,
            headers: { 'Content-Type' => 'application/json' }
          )
      end

      it 'returns safety validation result' do
        result = client.validate_safety(content: content)

        expect(result[:passed]).to be true
        expect(result[:pii_detected]).to be false
        expect(result[:moderation_flagged]).to be false
        expect(result[:issues]).to be_empty
      end
    end

    context 'when content contains PII' do
      let(:unsafe_response) do
        {
          passed: false,
          pii_detected: true,
          moderation_flagged: false,
          issues: ['PII detected in content']
        }
      end

      before do
        stub_request(:post, "#{ai_service_url}/api/v1/validate-safety")
          .to_return(
            status: 200,
            body: unsafe_response.to_json
          )
      end

      it 'returns failed validation with PII detection' do
        result = client.validate_safety(content: 'SSN: 123-45-6789')

        expect(result[:passed]).to be false
        expect(result[:pii_detected]).to be true
        expect(result[:issues]).to include('PII detected in content')
      end
    end

    context 'when AI service errors' do
      before do
        stub_request(:post, "#{ai_service_url}/api/v1/validate-safety")
          .to_return(status: 500)
      end

      it 'raises an error' do
        expect {
          client.validate_safety(content: content)
        }.to raise_error(/AI Service error/)
      end
    end
  end

  describe 'base_uri configuration' do
    it 'uses AI_SERVICE_URL from environment' do
      expect(described_class.base_uri).to eq(ai_service_url)
    end

    it 'defaults to localhost when not configured' do
      ClimateControl.modify AI_SERVICE_URL: nil do
        expect(described_class.base_uri).to eq('http://localhost:8000')
      end
    end
  end

  describe 'error handling' do
    context 'with network errors' do
      before do
        stub_request(:post, "#{ai_service_url}/api/v1/generate-lesson")
          .to_raise(SocketError.new('Connection refused'))
      end

      it 'propagates network errors' do
        expect {
          client.generate_lesson(topic: 'Test')
        }.to raise_error(SocketError)
      end
    end

    context 'with timeout errors' do
      before do
        stub_request(:post, "#{ai_service_url}/api/v1/generate-lesson")
          .to_timeout
      end

      it 'propagates timeout errors' do
        expect {
          client.generate_lesson(topic: 'Test')
        }.to raise_error(Net::OpenTimeout)
      end
    end
  end
end
