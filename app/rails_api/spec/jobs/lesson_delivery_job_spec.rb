# frozen_string_literal: true

require 'rails_helper'

RSpec.describe LessonDeliveryJob, type: :job do
  let(:learner) { create(:learner) }
  let(:learning_path) { create(:learning_path, learner: learner) }
  let(:service) { instance_double(LessonDeliveryService) }

  describe '#perform' do
    before do
      allow(LessonDeliveryService).to receive(:new).and_return(service)
      allow(service).to receive(:generate_and_deliver_lesson)
    end

    context 'with default email channel' do
      it 'finds the learning path' do
        expect(LearningPath).to receive(:find).with(learning_path.id)
          .and_return(learning_path)

        described_class.new.perform(learning_path.id)
      end

      it 'initializes delivery service with learning path' do
        expect(LessonDeliveryService).to receive(:new).with(learning_path)
          .and_return(service)

        described_class.new.perform(learning_path.id)
      end

      it 'calls generate_and_deliver_lesson with email channel' do
        expect(service).to receive(:generate_and_deliver_lesson)
          .with(channel: 'email')

        described_class.new.perform(learning_path.id)
      end
    end

    context 'with Slack channel' do
      it 'delivers via Slack' do
        expect(service).to receive(:generate_and_deliver_lesson)
          .with(channel: 'slack')

        described_class.new.perform(learning_path.id, channel: 'slack')
      end
    end

    context 'with SMS channel' do
      it 'delivers via SMS' do
        expect(service).to receive(:generate_and_deliver_lesson)
          .with(channel: 'sms')

        described_class.new.perform(learning_path.id, channel: 'sms')
      end
    end

    context 'when learning path does not exist' do
      it 'raises ActiveRecord::RecordNotFound' do
        expect {
          described_class.new.perform(999999)
        }.to raise_error(ActiveRecord::RecordNotFound)
      end
    end

    context 'when service raises an error' do
      before do
        allow(service).to receive(:generate_and_deliver_lesson)
          .and_raise(StandardError.new('Service error'))
      end

      it 'propagates the error' do
        expect {
          described_class.new.perform(learning_path.id)
        }.to raise_error(StandardError, /Service error/)
      end
    end
  end

  describe 'queue configuration' do
    it 'is in the default queue' do
      expect(described_class.new.queue_name).to eq('default')
    end
  end

  describe 'job execution' do
    include ActiveJob::TestHelper

    before do
      allow(LessonDeliveryService).to receive(:new).and_return(service)
      allow(service).to receive(:generate_and_deliver_lesson)
    end

    it 'enqueues the job' do
      expect {
        described_class.perform_later(learning_path.id)
      }.to have_enqueued_job(described_class)
        .with(learning_path.id)
        .on_queue('default')
    end

    it 'enqueues with custom channel' do
      expect {
        described_class.perform_later(learning_path.id, channel: 'slack')
      }.to have_enqueued_job(described_class)
        .with(learning_path.id, channel: 'slack')
    end

    it 'executes enqueued job' do
      described_class.perform_later(learning_path.id, channel: 'email')

      perform_enqueued_jobs

      expect(service).to have_received(:generate_and_deliver_lesson)
        .with(channel: 'email')
    end
  end

  describe 'retry behavior' do
    it 'inherits retry behavior from ApplicationJob' do
      # ApplicationJob may have retry configuration
      # This test verifies the job class structure
      expect(described_class.superclass).to eq(ApplicationJob)
    end
  end

  describe 'real integration' do
    let(:ai_client) { instance_double(AiServiceClient) }
    let(:ai_response) do
      {
        lesson: {
          topic: 'Test Topic',
          content: 'Test Content',
          key_points: ['Point 1'],
          scenario: 'Scenario',
          quiz_question: 'Question?',
          quiz_options: ['A', 'B'],
          correct_answer: 'A'
        },
        metadata: {},
        safety_check: { passed: true }
      }
    end

    before do
      allow(LessonDeliveryService).to receive(:new).and_call_original
      allow(AiServiceClient).to receive(:new).and_return(ai_client)
      allow(ai_client).to receive(:generate_lesson).and_return(ai_response)
    end

    it 'creates a lesson and delivers it' do
      expect {
        described_class.new.perform(learning_path.id, channel: 'email')
      }.to change { Lesson.count }.by(1)

      lesson = Lesson.last
      expect(lesson.delivered?).to be true
      expect(lesson.delivery_channel).to eq('email')
    end
  end
end
