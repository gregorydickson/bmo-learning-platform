require_relative "boot"

require "rails/all"

# Require the gems listed in Gemfile, including any gems
# you've limited to :test, :development, or :production.
Bundler.require(*Rails.groups)

module BmoLearningApi
  class Application < Rails::Application
    # Initialize configuration defaults for originally generated Rails version.
    config.load_defaults 7.2

    # Configuration for the application, engines, and railties goes here.
    #
    # These settings can be overridden in specific environments using the files
    # in config/environments, which are processed later.

    # API-only application
    config.api_only = true

    # CORS Configuration
    config.middleware.insert_before 0, Rack::Cors do
      allow do
        origins ENV.fetch("ALLOWED_ORIGINS", "http://localhost:3001").split(",")
        resource "*",
          headers: :any,
          methods: [:get, :post, :put, :patch, :delete, :options],
          credentials: true
      end
    end

    # Content Security Policy
    config.middleware.use ActionDispatch::ContentSecurityPolicy::Middleware

    # Timezone
    config.time_zone = "UTC"

    # Active Job configuration
    config.active_job.queue_adapter = :sidekiq

    # Autoload paths
    config.autoload_paths << Rails.root.join("lib")
  end
end
