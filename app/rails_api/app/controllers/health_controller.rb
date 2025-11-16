# frozen_string_literal: true

class HealthController < ApplicationController
  def show
    render json: {
      status: 'healthy',
      service: 'rails_api',
      timestamp: Time.current.iso8601
    }
  end
end
