Rails.application.routes.draw do
  # Health check endpoint
  get '/health', to: 'health#show'

  # API routes
  namespace :api do
    namespace :v1 do
      resources :learners, only: [:index, :show, :create, :update] do
        member do
          get :progress
        end
      end

      resources :learning_paths, only: [:create, :show, :index]

      resources :quiz_responses, only: [:create]

      resources :documents, only: [:index, :show, :create, :destroy] do
        member do
          get :download_url
        end
      end

      get '/analytics/dashboard', to: 'analytics#dashboard'
    end
  end
end
