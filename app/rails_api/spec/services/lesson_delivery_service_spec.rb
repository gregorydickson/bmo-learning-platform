# frozen_string_literal: true

require 'rails_helper'

RSpec.describe LessonDeliveryService do
  let(:learner) { create(:learner) }
  let(:learning_path) { create(:learning_path, learner: learner) }
  let(:service) { described_class.new(learning_path) }
  let(:ai_client) { instance_double(AiServiceClient) }

  let(:ai_response) do
    {
      lesson: {
        topic: 'Python Functions',
        content: 'Functions are reusable blocks of code...',
        key_points: ['Reusability', 'Parameters', 'Return values'],
        scenario: 'Building a calculator app...',
        quiz_question: 'What keyword defines a function?',
        quiz_options: ['func', 'def', 'function', 'define'],
        correct_answer: 'def'
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
    allow(AiServiceClient).to receive(:new).and_return(ai_client)
    allow(ai_client).to receive(:generate_lesson).and_return(ai_response)
  end

  describe '#initialize' do
    it 'sets learning_path' do
      expect(service.learning_path).to eq(learning_path)
    end

    it 'initializes AI client' do
      expect(AiServiceClient).to receive(:new)
      described_class.new(learning_path)
    end
  end

  describe '#generate_and_deliver_lesson' do
    context 'with email delivery (default)' do
      it 'calls AI service with correct parameters' do
        expect(ai_client).to receive(:generate_lesson).with(
          topic: learning_path.topic,
          learner_id: learning_path.learner_id.to_s
        )

        service.generate_and_deliver_lesson
      end

      it 'creates lesson record with AI response data' do
        expect {
          service.generate_and_deliver_lesson
        }.to change { learning_path.lessons.count }.by(1)

        lesson = learning_path.lessons.last
        expect(lesson.topic).to eq('Python Functions')
        expect(lesson.content).to eq('Functions are reusable blocks of code...')
        expect(lesson.quiz_question).to eq('What keyword defines a function?')
      end

      it 'marks lesson as delivered via email' do
        lesson = service.generate_and_deliver_lesson

        expect(lesson.delivered?).to be true
        expect(lesson.delivery_channel).to eq('email')
      end

      it 'logs email delivery' do
        expect(Rails.logger).to receive(:info).with(/Delivering lesson .* via email/)
        service.generate_and_deliver_lesson
      end

      it 'returns the created lesson' do
        lesson = service.generate_and_deliver_lesson

        expect(lesson).to be_a(Lesson)
        expect(lesson).to be_persisted
      end
    end

    context 'with Slack delivery' do
      it 'delivers via Slack' do
        expect(Rails.logger).to receive(:info).with(/Delivering lesson .* via Slack/)

        lesson = service.generate_and_deliver_lesson(channel: 'slack')

        expect(lesson.delivery_channel).to eq('slack')
      end
    end

    context 'with SMS delivery' do
      it 'delivers via SMS' do
        expect(Rails.logger).to receive(:info).with(/Delivering lesson .* via SMS/)

        lesson = service.generate_and_deliver_lesson(channel: 'sms')

        expect(lesson.delivery_channel).to eq('sms')
      end
    end

    context 'with unknown delivery channel' do
      it 'defaults to email delivery' do
        expect(Rails.logger).to receive(:info).with(/Delivering lesson .* via email/)

        lesson = service.generate_and_deliver_lesson(channel: 'unknown')

        expect(lesson.delivery_channel).to eq('unknown')
      end
    end

    context 'when AI service fails' do
      before do
        allow(ai_client).to receive(:generate_lesson)
          .and_raise(StandardError.new('AI Service error'))
      end

      it 'propagates the error' do
        expect {
          service.generate_and_deliver_lesson
        }.to raise_error(StandardError, /AI Service error/)
      end

      it 'does not create a lesson' do
        expect {
          begin
            service.generate_and_deliver_lesson
          rescue StandardError
            # Catch error to check lesson count
          end
        }.not_to change { Lesson.count }
      end
    end

    context 'when lesson creation fails' do
      before do
        allow(learning_path.lessons).to receive(:create!)
          .and_raise(ActiveRecord::RecordInvalid.new)
      end

      it 'propagates the error' do
        expect {
          service.generate_and_deliver_lesson
        }.to raise_error(ActiveRecord::RecordInvalid)
      end
    end

    context 'when delivery fails' do
      before do
        # Allow lesson creation but fail on mark_delivered!
        allow_any_instance_of(Lesson).to receive(:mark_delivered!)
          .and_raise(StandardError.new('Delivery failed'))
      end

      it 'propagates the error' do
        expect {
          service.generate_and_deliver_lesson
        }.to raise_error(StandardError, /Delivery failed/)
      end

      it 'creates the lesson but fails delivery' do
        expect {
          begin
            service.generate_and_deliver_lesson
          rescue StandardError
            # Catch to verify lesson was created
          end
        }.to change { Lesson.count }.by(1)
      end
    end
  end

  describe 'private methods' do
    describe '#create_lesson' do
      it 'creates lesson with all required fields' do
        lesson_data = ai_response[:lesson]
        lesson = service.send(:create_lesson, lesson_data)

        expect(lesson.topic).to eq(lesson_data[:topic])
        expect(lesson.content).to eq(lesson_data[:content])
        expect(lesson.key_points).to eq(lesson_data[:key_points])
        expect(lesson.scenario).to eq(lesson_data[:scenario])
        expect(lesson.quiz_question).to eq(lesson_data[:quiz_question])
        expect(lesson.quiz_options).to eq(lesson_data[:quiz_options])
        expect(lesson.correct_answer).to eq(lesson_data[:correct_answer])
      end

      it 'associates lesson with learning path' do
        lesson_data = ai_response[:lesson]
        lesson = service.send(:create_lesson, lesson_data)

        expect(lesson.learning_path).to eq(learning_path)
      end
    end

    describe '#deliver_lesson' do
      let(:lesson) { create(:lesson, learning_path: learning_path) }

      it 'marks lesson as delivered with correct channel' do
        service.send(:deliver_lesson, lesson, 'email')

        expect(lesson.reload.delivered?).to be true
        expect(lesson.delivery_channel).to eq('email')
      end
    end
  end

  describe 'integration with real AI client' do
    let(:real_service) { described_class.new(learning_path) }

    before do
      # Remove stub to test real integration (would need VCR in real scenario)
      allow(AiServiceClient).to receive(:new).and_call_original
    end

    it 'initializes with real AI client' do
      expect(real_service.instance_variable_get(:@ai_client))
        .to be_an_instance_of(AiServiceClient)
    end
  end
end
