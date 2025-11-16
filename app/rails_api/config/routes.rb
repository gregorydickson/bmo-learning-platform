Rails.application.routes.draw do
  # Health check endpoint
  get '/health', to: 'health#show'

  # API routes
  namespace :api do
    namespace :v1 do
      # API endpoints will be added in Phase 3
    end
  end
end
