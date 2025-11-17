# frozen_string_literal: true

require 'rails_helper'

RSpec.describe 'Api::V1::Learners', type: :request do
  let(:json) { JSON.parse(response.body) }

  describe 'GET /api/v1/learners' do
    let!(:learners) { create_list(:learner, 3) }

    it 'returns all learners' do
      get '/api/v1/learners'

      expect(response).to have_http_status(:ok)
      expect(json.length).to eq(3)
    end

    it 'returns JSON content type' do
      get '/api/v1/learners'

      expect(response.content_type).to include('application/json')
    end

    context 'when no learners exist' do
      before { Learner.destroy_all }

      it 'returns empty array' do
        get '/api/v1/learners'

        expect(response).to have_http_status(:ok)
        expect(json).to eq([])
      end
    end
  end

  describe 'GET /api/v1/learners/:id' do
    let(:learner) { create(:learner) }

    it 'returns the learner' do
      get "/api/v1/learners/#{learner.id}"

      expect(response).to have_http_status(:ok)
      expect(json['id']).to eq(learner.id)
      expect(json['email']).to eq(learner.email)
      expect(json['name']).to eq(learner.name)
    end

    context 'when learner does not exist' do
      it 'returns 404' do
        get '/api/v1/learners/999999'

        expect(response).to have_http_status(:not_found)
      end
    end
  end

  describe 'POST /api/v1/learners' do
    let(:valid_attributes) do
      {
        learner: {
          email: 'test@example.com',
          name: 'Test User',
          phone: '555-1234',
          slack_user_id: 'U12345'
        }
      }
    end

    context 'with valid parameters' do
      it 'creates a new learner' do
        expect {
          post '/api/v1/learners', params: valid_attributes
        }.to change(Learner, :count).by(1)
      end

      it 'returns 201 created' do
        post '/api/v1/learners', params: valid_attributes

        expect(response).to have_http_status(:created)
      end

      it 'returns the created learner' do
        post '/api/v1/learners', params: valid_attributes

        expect(json['email']).to eq('test@example.com')
        expect(json['name']).to eq('Test User')
        expect(json['phone']).to eq('555-1234')
        expect(json['slack_user_id']).to eq('U12345')
      end
    end

    context 'with invalid parameters' do
      let(:invalid_attributes) do
        {
          learner: {
            email: '',
            name: ''
          }
        }
      end

      it 'does not create a learner' do
        expect {
          post '/api/v1/learners', params: invalid_attributes
        }.not_to change(Learner, :count)
      end

      it 'returns 422 unprocessable entity' do
        post '/api/v1/learners', params: invalid_attributes

        expect(response).to have_http_status(:unprocessable_entity)
      end

      it 'returns error messages' do
        post '/api/v1/learners', params: invalid_attributes

        expect(json['errors']).to be_present
        expect(json['errors']['email']).to include("can't be blank")
        expect(json['errors']['name']).to include("can't be blank")
      end
    end

    context 'with duplicate email' do
      let!(:existing_learner) { create(:learner, email: 'test@example.com') }

      it 'returns validation error' do
        post '/api/v1/learners', params: valid_attributes

        expect(response).to have_http_status(:unprocessable_entity)
        expect(json['errors']['email']).to include('has already been taken')
      end
    end

    context 'with invalid email format' do
      let(:invalid_email_attributes) do
        {
          learner: {
            email: 'invalid_email',
            name: 'Test User'
          }
        }
      end

      it 'returns validation error' do
        post '/api/v1/learners', params: invalid_email_attributes

        expect(response).to have_http_status(:unprocessable_entity)
        expect(json['errors']['email']).to be_present
      end
    end
  end

  describe 'PATCH /api/v1/learners/:id' do
    let(:learner) { create(:learner) }

    context 'with valid parameters' do
      let(:new_attributes) do
        {
          learner: {
            name: 'Updated Name',
            phone: '555-9999'
          }
        }
      end

      it 'updates the learner' do
        patch "/api/v1/learners/#{learner.id}", params: new_attributes

        learner.reload
        expect(learner.name).to eq('Updated Name')
        expect(learner.phone).to eq('555-9999')
      end

      it 'returns the updated learner' do
        patch "/api/v1/learners/#{learner.id}", params: new_attributes

        expect(response).to have_http_status(:ok)
        expect(json['name']).to eq('Updated Name')
        expect(json['phone']).to eq('555-9999')
      end
    end

    context 'with invalid parameters' do
      let(:invalid_attributes) do
        {
          learner: {
            email: ''
          }
        }
      end

      it 'returns 422 unprocessable entity' do
        patch "/api/v1/learners/#{learner.id}", params: invalid_attributes

        expect(response).to have_http_status(:unprocessable_entity)
      end

      it 'does not update the learner' do
        original_email = learner.email
        patch "/api/v1/learners/#{learner.id}", params: invalid_attributes

        learner.reload
        expect(learner.email).to eq(original_email)
      end
    end

    context 'when learner does not exist' do
      it 'returns 404' do
        patch '/api/v1/learners/999999', params: { learner: { name: 'Test' } }

        expect(response).to have_http_status(:not_found)
      end
    end
  end

  describe 'GET /api/v1/learners/:id/progress' do
    let(:learner) { create(:learner) }

    context 'with learning paths and quiz responses' do
      before do
        path1 = create(:learning_path, learner: learner, total_lessons: 10, lessons_completed: 5, topic: 'Python')
        path2 = create(:learning_path, learner: learner, total_lessons: 20, lessons_completed: 10, topic: 'JavaScript')

        create_list(:quiz_response, 3, learner: learner, correct: true)
        create_list(:quiz_response, 2, learner: learner, correct: false)
      end

      it 'returns progress data' do
        get "/api/v1/learners/#{learner.id}/progress"

        expect(response).to have_http_status(:ok)
      end

      it 'includes learner_id' do
        get "/api/v1/learners/#{learner.id}/progress"

        expect(json['learner_id']).to eq(learner.id)
      end

      it 'includes completion_rate' do
        get "/api/v1/learners/#{learner.id}/progress"

        # Total: 30 lessons, Completed: 15 = 50%
        expect(json['completion_rate']).to eq(50.0)
      end

      it 'includes quiz_accuracy' do
        get "/api/v1/learners/#{learner.id}/progress"

        # 3 correct out of 5 total = 60%
        expect(json['quiz_accuracy']).to eq(60.0)
      end

      it 'includes learning paths data' do
        get "/api/v1/learners/#{learner.id}/progress"

        expect(json['learning_paths']).to be_an(Array)
        expect(json['learning_paths'].length).to eq(2)
      end

      it 'includes learning path details' do
        get "/api/v1/learners/#{learner.id}/progress"

        path_data = json['learning_paths'].first
        expect(path_data).to have_key('id')
        expect(path_data).to have_key('topic')
        expect(path_data).to have_key('status')
        expect(path_data).to have_key('progress')
      end
    end

    context 'with no learning paths' do
      it 'returns zero completion rate' do
        get "/api/v1/learners/#{learner.id}/progress"

        expect(json['completion_rate']).to eq(0)
        expect(json['quiz_accuracy']).to eq(0)
        expect(json['learning_paths']).to eq([])
      end
    end

    context 'when learner does not exist' do
      it 'returns 404' do
        get '/api/v1/learners/999999/progress'

        expect(response).to have_http_status(:not_found)
      end
    end
  end

  describe 'parameter filtering' do
    it 'filters allowed parameters for create' do
      params = {
        learner: {
          email: 'test@example.com',
          name: 'Test',
          phone: '555-1234',
          slack_user_id: 'U123',
          unauthorized_field: 'should be filtered'
        }
      }

      post '/api/v1/learners', params: params

      expect(Learner.last.attributes).not_to have_key('unauthorized_field')
    end
  end
end
