# frozen_string_literal: true

require 'rails_helper'

RSpec.describe 'Health Check', type: :request do
  describe 'GET /health' do
    it 'returns healthy status' do
      get '/health'

      expect(response).to have_http_status(:success)
      json = JSON.parse(response.body)
      expect(json['status']).to eq('healthy')
      expect(json['service']).to eq('rails_api')
      expect(json['timestamp']).to be_present
    end
  end
end
