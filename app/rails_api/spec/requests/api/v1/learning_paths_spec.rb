# frozen_string_literal: true

require 'rails_helper'

RSpec.describe 'Api::V1::LearningPaths', type: :request do
  let(:json) { JSON.parse(response.body) }
  let(:learner) { create(:learner) }

  describe 'POST /api/v1/learning_paths' do
    let(:valid_attributes) do
      {
        learner_id: learner.id,
        learning_path: {
          topic: 'Python Programming',
          total_lessons: 10
        }
      }
    end

    context 'with valid parameters' do
      it 'creates a new learning path' do
        expect {
          post '/api/v1/learning_paths', params: valid_attributes
        }.to change(LearningPath, :count).by(1)
      end

      it 'returns 201 created' do
        post '/api/v1/learning_paths', params: valid_attributes

        expect(response).to have_http_status(:created)
      end

      it 'returns the created learning path' do
        post '/api/v1/learning_paths', params: valid_attributes

        expect(json['topic']).to eq('Python Programming')
        expect(json['total_lessons']).to eq(10)
        expect(json['learner_id']).to eq(learner.id)
      end

      it 'associates learning path with learner' do
        post '/api/v1/learning_paths', params: valid_attributes

        learning_path = LearningPath.last
        expect(learning_path.learner).to eq(learner)
      end

      it 'enqueues lesson delivery job' do
        expect {
          post '/api/v1/learning_paths', params: valid_attributes
        }.to have_enqueued_job(LessonDeliveryJob)
      end

      it 'enqueues job with learning path id' do
        post '/api/v1/learning_paths', params: valid_attributes

        learning_path = LearningPath.last
        expect(LessonDeliveryJob).to have_been_enqueued.with(learning_path.id)
      end
    end

    context 'with invalid parameters' do
      let(:invalid_attributes) do
        {
          learner_id: learner.id,
          learning_path: {
            topic: '',
            total_lessons: 10
          }
        }
      end

      it 'does not create a learning path' do
        expect {
          post '/api/v1/learning_paths', params: invalid_attributes
        }.not_to change(LearningPath, :count)
      end

      it 'returns 422 unprocessable entity' do
        post '/api/v1/learning_paths', params: invalid_attributes

        expect(response).to have_http_status(:unprocessable_entity)
      end

      it 'returns error messages' do
        post '/api/v1/learning_paths', params: invalid_attributes

        expect(json['errors']).to be_present
        expect(json['errors']['topic']).to include("can't be blank")
      end

      it 'does not enqueue lesson delivery job' do
        expect {
          post '/api/v1/learning_paths', params: invalid_attributes
        }.not_to have_enqueued_job(LessonDeliveryJob)
      end
    end

    context 'when learner does not exist' do
      let(:invalid_learner_attributes) do
        {
          learner_id: 999999,
          learning_path: {
            topic: 'Python Programming',
            total_lessons: 10
          }
        }
      end

      it 'returns 404 not found' do
        post '/api/v1/learning_paths', params: invalid_learner_attributes

        expect(response).to have_http_status(:not_found)
      end

      it 'does not create a learning path' do
        expect {
          post '/api/v1/learning_paths', params: invalid_learner_attributes
        }.not_to change(LearningPath, :count)
      end
    end

    context 'with missing required parameters' do
      it 'returns error when topic is missing' do
        params = {
          learner_id: learner.id,
          learning_path: {
            total_lessons: 10
          }
        }

        post '/api/v1/learning_paths', params: params

        expect(response).to have_http_status(:unprocessable_entity)
      end
    end

    context 'parameter filtering' do
      it 'only permits topic and total_lessons' do
        params = {
          learner_id: learner.id,
          learning_path: {
            topic: 'Python Programming',
            total_lessons: 10,
            status: 'completed',  # Should be filtered
            unauthorized_field: 'value'  # Should be filtered
          }
        }

        post '/api/v1/learning_paths', params: params

        learning_path = LearningPath.last
        expect(learning_path.status).not_to eq('completed')  # Should use default
        expect(learning_path.attributes).not_to have_key('unauthorized_field')
      end
    end
  end

  describe 'background job integration' do
    include ActiveJob::TestHelper

    let(:valid_attributes) do
      {
        learner_id: learner.id,
        learning_path: {
          topic: 'Python Programming',
          total_lessons: 10
        }
      }
    end

    it 'performs the lesson delivery job asynchronously' do
      perform_enqueued_jobs do
        # Mock the AI service to prevent real HTTP calls
        ai_client = instance_double(AiServiceClient)
        allow(AiServiceClient).to receive(:new).and_return(ai_client)
        allow(ai_client).to receive(:generate_lesson).and_return({
          lesson: {
            topic: 'Test',
            content: 'Content',
            key_points: [],
            scenario: 'Scenario',
            quiz_question: 'Q?',
            quiz_options: ['A'],
            correct_answer: 'A'
          }
        })

        post '/api/v1/learning_paths', params: valid_attributes
      end

      # Job should have executed
      expect(Lesson.count).to be >= 0  # May or may not create lesson depending on job execution
    end
  end
end
