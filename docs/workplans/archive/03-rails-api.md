# Phase 3: Rails API Service

**Duration**: 10-12 days
**Goal**: Build production-grade Rails API with functional programming patterns, multi-channel delivery, and robust domain models

## Overview
This phase implements the Rails API service that orchestrates the learning platform. We prioritize:
1. **Domain-Driven Design** (rich domain models with clear boundaries)
2. **Functional Patterns** (dry-monads for error handling, service objects)
3. **Multi-Channel Delivery** (Slack, SMS, Email with unified interface)
4. **Background Processing** (Sidekiq for async operations)
5. **Production Readiness** (circuit breakers, rate limiting, monitoring)

## Prerequisites
- [ ] Phase 2 complete (LangChain AI service running)
- [ ] Ruby 3.2+ installed
- [ ] PostgreSQL 15+ running
- [ ] Redis running (for Sidekiq)
- [ ] Understanding of dry-monads and Railway Oriented Programming

## API Versions Used
```ruby
Rails 7.2.3
Ruby 3.2.0
```

```ruby
# Key gems versions
gem 'dry-monads', '~> 1.6'
gem 'sidekiq', '~> 7.1'
gem 'faraday', '~> 2.7'
gem 'rack-attack', '~> 6.7'
```

## 1. Rails Application Bootstrap

### 1.1 Create Rails API Application
- [ ] Generate Rails API-only application
  ```bash
  cd app
  rails new rails_api \
    --api \
    --database=postgresql \
    --skip-action-cable \
    --skip-action-mailbox \
    --skip-action-text \
    --skip-active-storage \
    -T  # Skip default test framework (we'll use RSpec)

  cd rails_api
  ```

- [ ] Configure database in `config/database.yml`
  ```yaml
  default: &default
    adapter: postgresql
    encoding: unicode
    pool: <%= ENV.fetch("RAILS_MAX_THREADS") { 5 } %>
    host: <%= ENV.fetch("DB_HOST") { "localhost" } %>
    username: <%= ENV.fetch("DB_USER") { "postgres" } %>
    password: <%= ENV.fetch("DB_PASSWORD") { "postgres" } %>

  development:
    <<: *default
    database: bmo_learning_development

  test:
    <<: *default
    database: bmo_learning_test

  production:
    <<: *default
    database: <%= ENV['DB_NAME'] %>
  ```

- [ ] Add essential gems to `Gemfile`
  ```ruby
  # Gemfile
  ruby '3.2.0'

  gem 'rails', '~> 7.2.3'
  gem 'pg', '~> 1.5'
  gem 'puma', '~> 6.0'

  # Functional programming
  gem 'dry-monads', '~> 1.6'
  gem 'dry-validation', '~> 1.10'
  gem 'dry-types', '~> 1.7'

  # Background jobs
  gem 'sidekiq', '~> 7.1'
  gem 'sidekiq-scheduler', '~> 5.0'

  # External integrations
  gem 'faraday', '~> 2.7'
  gem 'faraday-retry', '~> 2.2'
  gem 'slack-ruby-client', '~> 2.1'
  gem 'twilio-ruby', '~> 6.6'

  # Circuit breaker
  gem 'circuitbox', '~> 2.0'

  # Authentication & Authorization
  gem 'jwt', '~> 2.7'
  gem 'bcrypt', '~> 3.1'
  gem 'pundit', '~> 2.3'

  # Rate limiting
  gem 'rack-attack', '~> 6.7'

  # Serialization
  gem 'jsonapi-serializer', '~> 2.2'

  # Monitoring
  gem 'sentry-ruby', '~> 5.14'
  gem 'sentry-rails', '~> 5.14'

  # CORS
  gem 'rack-cors', '~> 2.0'

  group :development, :test do
    gem 'rspec-rails', '~> 6.1'
    gem 'factory_bot_rails', '~> 6.4'
    gem 'faker', '~> 3.2'
    gem 'pry-rails', '~> 0.3'
    gem 'rubocop', '~> 1.57', require: false
    gem 'rubocop-rails', '~> 2.22', require: false
    gem 'rubocop-rspec', '~> 2.25', require: false
  end

  group :test do
    gem 'shoulda-matchers', '~> 5.3'
    gem 'webmock', '~> 3.19'
    gem 'vcr', '~> 6.2'
    gem 'simplecov', '~> 0.22', require: false
  end
  ```

**Validation**: `bundle install && rails db:create` succeeds

### 1.2 Configure RSpec
- [ ] Install RSpec
  ```bash
  rails generate rspec:install
  ```

- [ ] Configure `spec/rails_helper.rb`
  ```ruby
  require 'spec_helper'
  require File.expand_path('../config/environment', __dir__)
  abort("The Rails environment is running in production mode!") if Rails.env.production?
  require 'rspec/rails'
  require 'webmock/rspec'
  require 'vcr'

  # Configure SimpleCov
  require 'simplecov'
  SimpleCov.start 'rails' do
    add_filter '/spec/'
    add_filter '/config/'
    minimum_coverage 80
  end

  # Load support files
  Dir[Rails.root.join('spec', 'support', '**', '*.rb')].sort.each { |f| require f }

  RSpec.configure do |config|
    config.fixture_path = Rails.root.join('spec/fixtures')
    config.use_transactional_fixtures = true
    config.infer_spec_type_from_file_location!
    config.filter_rails_from_backtrace!

    # FactoryBot
    config.include FactoryBot::Syntax::Methods

    # Shoulda Matchers
    Shoulda::Matchers.configure do |shoulda_config|
      shoulda_config.integrate do |with|
        with.test_framework :rspec
        with.library :rails
      end
    end
  end

  # VCR configuration
  VCR.configure do |config|
    config.cassette_library_dir = 'spec/vcr_cassettes'
    config.hook_into :webmock
    config.configure_rspec_metadata!
    config.filter_sensitive_data('<OPENAI_API_KEY>') { ENV['OPENAI_API_KEY'] }
    config.filter_sensitive_data('<TWILIO_ACCOUNT_SID>') { ENV['TWILIO_ACCOUNT_SID'] }
  end
  ```

**Validation**: `rspec` runs successfully (0 examples)

## 2. Domain Models

### 2.1 Learner Model
- [ ] Generate migration and model
  ```bash
  rails generate model Learner \
    employee_id:string:uniq \
    first_name:string \
    last_name:string \
    email:string:uniq \
    phone:string \
    role:string \
    knowledge_level:string \
    onboarding_completed:boolean \
    slack_user_id:string \
    preferred_channel:string \
    metadata:jsonb
  ```

- [ ] Create `app/models/learner.rb`
  ```ruby
  # app/models/learner.rb
  class Learner < ApplicationRecord
    # Validations
    validates :employee_id, presence: true, uniqueness: true
    validates :email, presence: true, uniqueness: true, format: { with: URI::MailTo::EMAIL_REGEXP }
    validates :first_name, :last_name, presence: true
    validates :role, presence: true, inclusion: { in: %w[sales_associate manager regional_director] }
    validates :knowledge_level, inclusion: { in: %w[beginner intermediate advanced] }, allow_nil: true
    validates :preferred_channel, inclusion: { in: %w[slack sms email] }

    # Associations
    has_many :learning_paths, dependent: :destroy
    has_many :assessment_results, dependent: :destroy
    has_many :engagement_metrics, dependent: :destroy

    # Scopes
    scope :onboarding, -> { where(onboarding_completed: false) }
    scope :active, -> { where(onboarding_completed: true) }
    scope :by_role, ->(role) { where(role: role) }

    # Methods
    def full_name
      "#{first_name} #{last_name}"
    end

    def beginner?
      knowledge_level == 'beginner'
    end

    def delivery_address
      case preferred_channel
      when 'slack' then slack_user_id
      when 'sms' then phone
      when 'email' then email
      else raise "Invalid channel: #{preferred_channel}"
      end
    end
  end
  ```

- [ ] Create RSpec test `spec/models/learner_spec.rb`
  ```ruby
  require 'rails_helper'

  RSpec.describe Learner, type: :model do
    describe 'validations' do
      it { should validate_presence_of(:employee_id) }
      it { should validate_presence_of(:email) }
      it { should validate_presence_of(:first_name) }
      it { should validate_presence_of(:last_name) }
      it { should validate_presence_of(:role) }

      it { should validate_uniqueness_of(:employee_id) }
      it { should validate_uniqueness_of(:email) }

      it { should allow_value('sales_associate').for(:role) }
      it { should_not allow_value('invalid_role').for(:role) }

      it { should allow_value('test@example.com').for(:email) }
      it { should_not allow_value('invalid_email').for(:email) }
    end

    describe 'associations' do
      it { should have_many(:learning_paths).dependent(:destroy) }
      it { should have_many(:assessment_results).dependent(:destroy) }
      it { should have_many(:engagement_metrics).dependent(:destroy) }
    end

    describe '#full_name' do
      it 'returns combined first and last name' do
        learner = build(:learner, first_name: 'John', last_name: 'Doe')
        expect(learner.full_name).to eq('John Doe')
      end
    end

    describe '#delivery_address' do
      it 'returns slack_user_id for slack channel' do
        learner = build(:learner, preferred_channel: 'slack', slack_user_id: 'U12345')
        expect(learner.delivery_address).to eq('U12345')
      end

      it 'returns phone for sms channel' do
        learner = build(:learner, preferred_channel: 'sms', phone: '+15551234567')
        expect(learner.delivery_address).to eq('+15551234567')
      end

      it 'returns email for email channel' do
        learner = build(:learner, preferred_channel: 'email', email: 'test@example.com')
        expect(learner.delivery_address).to eq('test@example.com')
      end
    end
  end
  ```

**Validation**: `rspec spec/models/learner_spec.rb` passes

### 2.2 LearningPath Model
- [ ] Generate migration
  ```bash
  rails generate model LearningPath \
    learner_id:references \
    name:string \
    status:string \
    difficulty:string \
    topics:jsonb \
    current_position:integer \
    completion_percentage:float \
    started_at:datetime \
    completed_at:datetime
  ```

- [ ] Create model `app/models/learning_path.rb`
  ```ruby
  class LearningPath < ApplicationRecord
    belongs_to :learner
    has_many :microlessons, dependent: :destroy

    validates :name, presence: true
    validates :status, presence: true, inclusion: { in: %w[not_started in_progress completed paused] }
    validates :difficulty, inclusion: { in: %w[beginner intermediate advanced] }
    validates :current_position, numericality: { greater_than_or_equal_to: 0 }
    validates :completion_percentage, numericality: { greater_than_or_equal_to: 0, less_than_or_equal_to: 100 }

    scope :active, -> { where(status: 'in_progress') }
    scope :completed, -> { where(status: 'completed') }

    def advance!
      increment!(:current_position)
      update_completion_percentage
    end

    def complete!
      update!(status: 'completed', completed_at: Time.current, completion_percentage: 100)
    end

    private

    def update_completion_percentage
      total_lessons = microlessons.count
      completed_lessons = microlessons.where(completed: true).count

      self.completion_percentage = total_lessons.zero? ? 0 : (completed_lessons.to_f / total_lessons * 100)
      save
    end
  end
  ```

### 2.3 Microlesson Model
- [ ] Generate migration
  ```bash
  rails generate model Microlesson \
    learning_path_id:references \
    topic:string \
    content:text \
    key_points:jsonb \
    scenario:text \
    quiz_question:string \
    quiz_options:jsonb \
    correct_answer:integer \
    position:integer \
    completed:boolean \
    completed_at:datetime
  ```

- [ ] Create model with validation
  ```ruby
  class Microlesson < ApplicationRecord
    belongs_to :learning_path

    validates :topic, :content, presence: true
    validates :position, numericality: { greater_than_or_equal_to: 0 }
    validates :correct_answer, numericality: { greater_than_or_equal_to: 0, less_than: 4 }, allow_nil: true

    scope :completed, -> { where(completed: true) }
    scope :ordered, -> { order(position: :asc) }

    def mark_completed!
      update!(completed: true, completed_at: Time.current)
      learning_path.advance!
    end
  end
  ```

### 2.4 AssessmentResult Model
- [ ] Generate migration
  ```bash
  rails generate model AssessmentResult \
    learner_id:references \
    microlesson_id:references \
    user_answer:integer \
    is_correct:boolean \
    time_taken_seconds:integer \
    attempted_at:datetime
  ```

- [ ] Create model
  ```ruby
  class AssessmentResult < ApplicationRecord
    belongs_to :learner
    belongs_to :microlesson

    validates :user_answer, presence: true, numericality: { greater_than_or_equal_to: 0, less_than: 4 }
    validates :is_correct, inclusion: { in: [true, false] }
    validates :attempted_at, presence: true

    scope :correct, -> { where(is_correct: true) }
    scope :incorrect, -> { where(is_correct: false) }
    scope :recent, -> { order(attempted_at: :desc) }

    def self.average_score_for_learner(learner_id)
      where(learner_id: learner_id).average('CAST(is_correct AS integer)').to_f * 100
    end
  end
  ```

### 2.5 EngagementMetric Model
- [ ] Generate migration
  ```bash
  rails generate model EngagementMetric \
    learner_id:references \
    event_type:string \
    event_data:jsonb \
    channel:string \
    recorded_at:datetime
  ```

- [ ] Create model
  ```ruby
  class EngagementMetric < ApplicationRecord
    belongs_to :learner

    validates :event_type, presence: true, inclusion: {
      in: %w[lesson_started lesson_completed assessment_taken reminder_sent channel_changed]
    }
    validates :channel, inclusion: { in: %w[slack sms email web] }
    validates :recorded_at, presence: true

    scope :by_type, ->(type) { where(event_type: type) }
    scope :by_channel, ->(channel) { where(channel: channel) }
    scope :recent, ->(days = 7) { where('recorded_at >= ?', days.days.ago) }
  end
  ```

**Validation**: `rails db:migrate && rspec spec/models` passes

## 3. Functional Service Layer with dry-monads

### 3.1 Base Service Class
- [ ] Create `app/services/application_service.rb`
  ```ruby
  # app/services/application_service.rb
  class ApplicationService
    include Dry::Monads[:result, :do]

    def self.call(...)
      new(...).call
    end

    def call
      raise NotImplementedError, "#{self.class} must implement #call"
    end
  end
  ```

### 3.2 Learner Registration Service
- [ ] Create `app/services/learners/registration_service.rb`
  ```ruby
  module Learners
    class RegistrationService < ApplicationService
      def initialize(params)
        @params = params
      end

      def call
        validated_params = yield validate_params
        learner = yield create_learner(validated_params)
        learning_path = yield create_initial_learning_path(learner)

        Success({ learner: learner, learning_path: learning_path })
      end

      private

      def validate_params
        schema = Dry::Validation.Contract do
          params do
            required(:employee_id).filled(:string)
            required(:email).filled(:string)
            required(:first_name).filled(:string)
            required(:last_name).filled(:string)
            required(:role).filled(:string, included_in?: %w[sales_associate manager regional_director])
            optional(:phone).maybe(:string)
            optional(:preferred_channel).filled(:string, included_in?: %w[slack sms email])
          end

          rule(:email) do
            key.failure('must be valid email') unless value.match?(URI::MailTo::EMAIL_REGEXP)
          end
        end

        result = schema.new.call(@params)
        result.success? ? Success(result.to_h) : Failure([:validation_error, result.errors.to_h])
      end

      def create_learner(params)
        learner = Learner.new(params)
        learner.save ? Success(learner) : Failure([:creation_failed, learner.errors])
      end

      def create_initial_learning_path(learner)
        path = learner.learning_paths.create!(
          name: "Onboarding Path",
          status: "not_started",
          difficulty: "beginner",
          topics: ["credit_cards_101", "apr_basics", "rewards_programs"],
          current_position: 0,
          completion_percentage: 0
        )
        Success(path)
      rescue StandardError => e
        Failure([:path_creation_failed, e.message])
      end
    end
  end
  ```

- [ ] Create RSpec test `spec/services/learners/registration_service_spec.rb`
  ```ruby
  require 'rails_helper'

  RSpec.describe Learners::RegistrationService do
    describe '#call' do
      context 'with valid parameters' do
        let(:params) do
          {
            employee_id: 'EMP123',
            email: 'john.doe@bmo.com',
            first_name: 'John',
            last_name: 'Doe',
            role: 'sales_associate',
            preferred_channel: 'slack'
          }
        end

        it 'creates learner and learning path' do
          result = described_class.call(params)

          expect(result).to be_success

          value = result.value!
          expect(value[:learner]).to be_a(Learner)
          expect(value[:learner].employee_id).to eq('EMP123')
          expect(value[:learning_path]).to be_a(LearningPath)
          expect(value[:learning_path].name).to eq('Onboarding Path')
        end
      end

      context 'with invalid email' do
        let(:params) do
          {
            employee_id: 'EMP123',
            email: 'invalid_email',
            first_name: 'John',
            last_name: 'Doe',
            role: 'sales_associate'
          }
        end

        it 'returns validation error' do
          result = described_class.call(params)

          expect(result).to be_failure
          type, errors = result.failure
          expect(type).to eq(:validation_error)
        end
      end
    end
  end
  ```

**Validation**: `rspec spec/services/learners/registration_service_spec.rb` passes

### 3.3 Lesson Generation Service
- [ ] Create `app/services/lessons/generation_service.rb`
  ```ruby
  module Lessons
    class GenerationService < ApplicationService
      def initialize(learning_path:, learner:)
        @learning_path = learning_path
        @learner = learner
      end

      def call
        topic = yield select_next_topic
        ai_lesson = yield generate_ai_content(topic)
        microlesson = yield save_microlesson(ai_lesson)

        Success(microlesson)
      end

      private

      def select_next_topic
        topics = @learning_path.topics
        current_pos = @learning_path.current_position

        if topics && topics[current_pos]
          Success(topics[current_pos])
        else
          Failure([:no_topics_remaining, "Learning path completed"])
        end
      end

      def generate_ai_content(topic)
        AiService::LessonClient.new.generate_lesson(
          topic: topic,
          learner_id: @learner.employee_id,
          difficulty: @learning_path.difficulty
        )
      end

      def save_microlesson(ai_lesson)
        microlesson = @learning_path.microlessons.create!(
          topic: ai_lesson[:topic],
          content: ai_lesson[:content],
          key_points: ai_lesson[:key_points],
          scenario: ai_lesson[:scenario],
          quiz_question: ai_lesson[:quiz_question],
          quiz_options: ai_lesson[:quiz_options],
          correct_answer: ai_lesson[:correct_answer],
          position: @learning_path.microlessons.count,
          completed: false
        )
        Success(microlesson)
      rescue StandardError => e
        Failure([:save_failed, e.message])
      end
    end
  end
  ```

## 4. AI Service Integration with Circuit Breaker

### 4.1 AI Service Client
- [ ] Create `app/clients/ai_service/lesson_client.rb`
  ```ruby
  module AiService
    class LessonClient
      include Dry::Monads[:result]

      AI_SERVICE_URL = ENV.fetch('AI_SERVICE_URL', 'http://localhost:8000')

      def generate_lesson(topic:, learner_id:, difficulty: 'medium')
        response = with_circuit_breaker do
          connection.post('/api/v1/generate-lesson') do |req|
            req.headers['Content-Type'] = 'application/json'
            req.body = {
              topic: topic,
              learner_id: learner_id,
              difficulty: difficulty
            }.to_json
          end
        end

        if response.success?
          lesson_data = JSON.parse(response.body, symbolize_names: true)
          Success(lesson_data[:lesson])
        else
          Failure([:ai_service_error, response.status])
        end
      rescue Faraday::Error => e
        Rails.logger.error("AI Service error: #{e.message}")
        Failure([:network_error, e.message])
      rescue Circuitbox::CircuitBreakerError => e
        Rails.logger.error("Circuit breaker open: #{e.message}")
        Failure([:circuit_open, "AI service temporarily unavailable"])
      end

      private

      def connection
        @connection ||= Faraday.new(url: AI_SERVICE_URL) do |f|
          f.request :retry, max: 2, interval: 0.5
          f.adapter Faraday.default_adapter
        end
      end

      def with_circuit_breaker(&block)
        circuit_breaker.run(&block)
      end

      def circuit_breaker
        @circuit_breaker ||= Circuitbox.circuit(:ai_service, {
          exceptions: [Faraday::Error],
          sleep_window: 30,
          time_window: 60,
          volume_threshold: 5,
          error_threshold: 50
        })
      end
    end
  end
  ```

- [ ] Create RSpec test with VCR `spec/clients/ai_service/lesson_client_spec.rb`
  ```ruby
  require 'rails_helper'

  RSpec.describe AiService::LessonClient do
    describe '#generate_lesson', :vcr do
      context 'when AI service responds successfully' do
        it 'returns lesson data' do
          client = described_class.new
          result = client.generate_lesson(
            topic: 'APR',
            learner_id: 'EMP123',
            difficulty: 'beginner'
          )

          expect(result).to be_success

          lesson = result.value!
          expect(lesson[:topic]).to eq('APR')
          expect(lesson[:content]).to be_present
          expect(lesson[:key_points]).to be_an(Array)
        end
      end

      context 'when AI service is unavailable' do
        before do
          stub_request(:post, "#{AiService::LessonClient::AI_SERVICE_URL}/api/v1/generate-lesson")
            .to_return(status: 503)
        end

        it 'returns failure' do
          client = described_class.new
          result = client.generate_lesson(
            topic: 'APR',
            learner_id: 'EMP123'
          )

          expect(result).to be_failure
        end
      end
    end
  end
  ```

**Validation**: `rspec spec/clients/ai_service/lesson_client_spec.rb` passes

## 5. Multi-Channel Delivery System

### 5.1 Unified Delivery Interface
- [ ] Create `app/services/delivery/base_channel.rb`
  ```ruby
  module Delivery
    class BaseChannel
      include Dry::Monads[:result]

      def deliver(recipient:, message:, metadata: {})
        raise NotImplementedError
      end

      protected

      def log_delivery(channel:, recipient:, success:, error: nil)
        Rails.logger.info(
          "Delivery attempt",
          channel: channel,
          recipient: recipient,
          success: success,
          error: error
        )
      end
    end
  end
  ```

### 5.2 Slack Channel
- [ ] Create `app/services/delivery/slack_channel.rb`
  ```ruby
  module Delivery
    class SlackChannel < BaseChannel
      def deliver(recipient:, message:, metadata: {})
        client.chat_postMessage(
          channel: recipient,
          text: message[:text],
          blocks: format_blocks(message)
        )

        log_delivery(channel: 'slack', recipient: recipient, success: true)
        Success({ channel: 'slack', delivered_at: Time.current })
      rescue Slack::Web::Api::Errors::SlackError => e
        log_delivery(channel: 'slack', recipient: recipient, success: false, error: e.message)
        Failure([:slack_error, e.message])
      end

      private

      def client
        @client ||= Slack::Web::Client.new(token: ENV['SLACK_BOT_TOKEN'])
      end

      def format_blocks(message)
        [
          {
            type: 'section',
            text: {
              type: 'mrkdwn',
              text: message[:text]
            }
          },
          message[:actions] ? {
            type: 'actions',
            elements: message[:actions]
          } : nil
        ].compact
      end
    end
  end
  ```

### 5.3 SMS Channel (Twilio)
- [ ] Create `app/services/delivery/sms_channel.rb`
  ```ruby
  module Delivery
    class SmsChannel < BaseChannel
      def deliver(recipient:, message:, metadata: {})
        client.messages.create(
          from: ENV['TWILIO_PHONE_NUMBER'],
          to: recipient,
          body: message[:text]
        )

        log_delivery(channel: 'sms', recipient: recipient, success: true)
        Success({ channel: 'sms', delivered_at: Time.current })
      rescue Twilio::REST::RestError => e
        log_delivery(channel: 'sms', recipient: recipient, success: false, error: e.message)
        Failure([:sms_error, e.message])
      end

      private

      def client
        @client ||= Twilio::REST::Client.new(
          ENV['TWILIO_ACCOUNT_SID'],
          ENV['TWILIO_AUTH_TOKEN']
        )
      end
    end
  end
  ```

### 5.4 Email Channel
- [ ] Create `app/mailers/learning_mailer.rb`
  ```ruby
  class LearningMailer < ApplicationMailer
    default from: 'learning@bmo.com'

    def microlesson(learner:, lesson:)
      @learner = learner
      @lesson = lesson

      mail(
        to: learner.email,
        subject: "Your Daily Lesson: #{lesson.topic}"
      )
    end
  end
  ```

- [ ] Create `app/services/delivery/email_channel.rb`
  ```ruby
  module Delivery
    class EmailChannel < BaseChannel
      def deliver(recipient:, message:, metadata: {})
        LearningMailer.microlesson(
          learner: metadata[:learner],
          lesson: metadata[:lesson]
        ).deliver_later

        log_delivery(channel: 'email', recipient: recipient, success: true)
        Success({ channel: 'email', delivered_at: Time.current })
      rescue StandardError => e
        log_delivery(channel: 'email', recipient: recipient, success: false, error: e.message)
        Failure([:email_error, e.message])
      end
    end
  end
  ```

### 5.5 Channel Router
- [ ] Create `app/services/delivery/router.rb`
  ```ruby
  module Delivery
    class Router
      include Dry::Monads[:result]

      CHANNELS = {
        'slack' => SlackChannel,
        'sms' => SmsChannel,
        'email' => EmailChannel
      }.freeze

      def self.deliver(learner:, message:, metadata: {})
        new(learner: learner).deliver(message: message, metadata: metadata)
      end

      def initialize(learner:)
        @learner = learner
      end

      def deliver(message:, metadata: {})
        channel_class = CHANNELS[@learner.preferred_channel]

        return Failure([:invalid_channel, @learner.preferred_channel]) unless channel_class

        channel_class.new.deliver(
          recipient: @learner.delivery_address,
          message: message,
          metadata: metadata.merge(learner: @learner)
        )
      end
    end
  end
  ```

**Validation**: Test delivery router with RSpec

## 6. Background Jobs with Sidekiq

### 6.1 Configure Sidekiq
- [ ] Create `config/sidekiq.yml`
  ```yaml
  :concurrency: 5
  :queues:
    - critical
    - default
    - low_priority
    - mailers

  :schedule:
    daily_lesson_dispatch:
      cron: '0 9 * * *'  # 9 AM daily
      class: DailyLessonDispatchJob
      queue: default

    engagement_metrics_aggregation:
      cron: '0 */6 * * *'  # Every 6 hours
      class: EngagementMetricsAggregationJob
      queue: low_priority
  ```

### 6.2 Daily Lesson Dispatch Job
- [ ] Create `app/jobs/daily_lesson_dispatch_job.rb`
  ```ruby
  class DailyLessonDispatchJob < ApplicationJob
    queue_as :default

    def perform
      Learner.active.find_each do |learner|
        LessonDeliveryJob.perform_later(learner.id)
      end
    end
  end
  ```

### 6.3 Lesson Delivery Job
- [ ] Create `app/jobs/lesson_delivery_job.rb`
  ```ruby
  class LessonDeliveryJob < ApplicationJob
    queue_as :default
    retry_on StandardError, wait: :exponentially_longer, attempts: 3

    def perform(learner_id)
      learner = Learner.find(learner_id)
      learning_path = learner.learning_paths.active.first

      return unless learning_path

      # Generate lesson
      result = Lessons::GenerationService.call(
        learning_path: learning_path,
        learner: learner
      )

      if result.success?
        microlesson = result.value!

        # Deliver via preferred channel
        Delivery::Router.deliver(
          learner: learner,
          message: format_lesson_message(microlesson),
          metadata: { lesson: microlesson }
        )

        # Track engagement
        EngagementMetric.create!(
          learner: learner,
          event_type: 'lesson_sent',
          channel: learner.preferred_channel,
          event_data: { microlesson_id: microlesson.id },
          recorded_at: Time.current
        )
      else
        Rails.logger.error("Lesson generation failed: #{result.failure}")
      end
    end

    private

    def format_lesson_message(lesson)
      {
        text: <<~TEXT
          📚 *#{lesson.topic}*

          #{lesson.content}

          🎯 *Key Points:*
          #{lesson.key_points.map { |point| "• #{point}" }.join("\n")}

          💡 *Scenario:*
          #{lesson.scenario}

          ❓ *Quiz:*
          #{lesson.quiz_question}

          #{lesson.quiz_options.each_with_index.map { |opt, i| "#{i + 1}. #{opt}" }.join("\n")}
        TEXT
      }
    end
  end
  ```

- [ ] Create RSpec test `spec/jobs/lesson_delivery_job_spec.rb`
  ```ruby
  require 'rails_helper'

  RSpec.describe LessonDeliveryJob, type: :job do
    include ActiveJob::TestHelper

    describe '#perform' do
      let(:learner) { create(:learner, preferred_channel: 'slack') }
      let(:learning_path) { create(:learning_path, learner: learner, status: 'in_progress') }

      before do
        allow(Lessons::GenerationService).to receive(:call).and_return(
          Dry::Monads::Success(create(:microlesson, learning_path: learning_path))
        )
        allow(Delivery::Router).to receive(:deliver).and_return(Dry::Monads::Success({}))
      end

      it 'generates and delivers lesson' do
        expect {
          perform_enqueued_jobs { described_class.perform_later(learner.id) }
        }.to change(EngagementMetric, :count).by(1)

        expect(Lessons::GenerationService).to have_received(:call)
        expect(Delivery::Router).to have_received(:deliver)
      end
    end
  end
  ```

**Validation**: `rspec spec/jobs/lesson_delivery_job_spec.rb` passes

## 7. API Endpoints

### 7.1 Authentication Middleware
- [ ] Create `app/controllers/concerns/authenticatable.rb`
  ```ruby
  module Authenticatable
    extend ActiveSupport::Concern

    included do
      before_action :authenticate_request
      attr_reader :current_user
    end

    private

    def authenticate_request
      header = request.headers['Authorization']
      token = header.split(' ').last if header

      begin
        decoded = JWT.decode(token, Rails.application.secret_key_base, true, algorithm: 'HS256')
        @current_user = Learner.find(decoded[0]['learner_id'])
      rescue JWT::DecodeError, ActiveRecord::RecordNotFound
        render json: { error: 'Unauthorized' }, status: :unauthorized
      end
    end
  end
  ```

### 7.2 Learners Controller
- [ ] Create `app/controllers/api/v1/learners_controller.rb`
  ```ruby
  module Api
    module V1
      class LearnersController < ApplicationController
        include Authenticatable
        skip_before_action :authenticate_request, only: [:create]

        def create
          result = Learners::RegistrationService.call(learner_params)

          if result.success?
            value = result.value!
            render json: LearnerSerializer.new(value[:learner]).serializable_hash, status: :created
          else
            type, errors = result.failure
            render json: { errors: errors }, status: :unprocessable_entity
          end
        end

        def show
          render json: LearnerSerializer.new(current_user).serializable_hash
        end

        private

        def learner_params
          params.require(:learner).permit(
            :employee_id, :email, :first_name, :last_name,
            :role, :phone, :preferred_channel
          )
        end
      end
    end
  end
  ```

### 7.3 Learning Paths Controller
- [ ] Create `app/controllers/api/v1/learning_paths_controller.rb`
  ```ruby
  module Api
    module V1
      class LearningPathsController < ApplicationController
        include Authenticatable

        def index
          paths = current_user.learning_paths
          render json: LearningPathSerializer.new(paths).serializable_hash
        end

        def show
          path = current_user.learning_paths.find(params[:id])
          render json: LearningPathSerializer.new(path, include: [:microlessons]).serializable_hash
        end

        def create
          path = current_user.learning_paths.create!(learning_path_params)
          render json: LearningPathSerializer.new(path).serializable_hash, status: :created
        rescue ActiveRecord::RecordInvalid => e
          render json: { errors: e.record.errors }, status: :unprocessable_entity
        end

        private

        def learning_path_params
          params.require(:learning_path).permit(:name, :difficulty, topics: [])
        end
      end
    end
  end
  ```

### 7.4 Assessments Controller
- [ ] Create `app/controllers/api/v1/assessments_controller.rb`
  ```ruby
  module Api
    module V1
      class AssessmentsController < ApplicationController
        include Authenticatable

        def submit
          microlesson = Microlesson.find(params[:microlesson_id])
          is_correct = microlesson.correct_answer == params[:answer].to_i

          result = current_user.assessment_results.create!(
            microlesson: microlesson,
            user_answer: params[:answer].to_i,
            is_correct: is_correct,
            time_taken_seconds: params[:time_taken],
            attempted_at: Time.current
          )

          microlesson.mark_completed! if is_correct

          render json: AssessmentResultSerializer.new(result).serializable_hash
        end
      end
    end
  end
  ```

**Validation**: Test controllers with RSpec request specs

## 8. Rate Limiting & Security

### 8.1 Configure Rack::Attack
- [ ] Create `config/initializers/rack_attack.rb`
  ```ruby
  class Rack::Attack
    # Throttle all requests by IP
    throttle('req/ip', limit: 300, period: 5.minutes) do |req|
      req.ip
    end

    # Throttle POST requests to /api/v1/learners by IP
    throttle('registrations/ip', limit: 5, period: 1.hour) do |req|
      req.ip if req.path == '/api/v1/learners' && req.post?
    end

    # Throttle login attempts
    throttle('logins/email', limit: 5, period: 20.minutes) do |req|
      req.params['email'] if req.path == '/api/v1/auth/login' && req.post?
    end
  end
  ```

### 8.2 Configure CORS
- [ ] Update `config/initializers/cors.rb`
  ```ruby
  Rails.application.config.middleware.insert_before 0, Rack::Cors do
    allow do
      origins ENV.fetch('ALLOWED_ORIGINS', 'http://localhost:3000').split(',')

      resource '*',
        headers: :any,
        methods: [:get, :post, :put, :patch, :delete, :options, :head],
        credentials: true
    end
  end
  ```

## 9. Testing Strategy

### 9.1 Factory Definitions
- [ ] Create `spec/factories/learners.rb`
  ```ruby
  FactoryBot.define do
    factory :learner do
      sequence(:employee_id) { |n| "EMP#{n.to_s.rjust(5, '0')}" }
      sequence(:email) { |n| "employee#{n}@bmo.com" }
      first_name { Faker::Name.first_name }
      last_name { Faker::Name.last_name }
      role { %w[sales_associate manager regional_director].sample }
      preferred_channel { 'slack' }
      knowledge_level { %w[beginner intermediate advanced].sample }
      onboarding_completed { false }
      slack_user_id { "U#{Faker::Alphanumeric.alpha(number: 10).upcase}" }
      phone { Faker::PhoneNumber.cell_phone }
    end
  end
  ```

- [ ] Create factories for all models (LearningPath, Microlesson, etc.)

### 9.2 Request Specs
- [ ] Create `spec/requests/api/v1/learners_spec.rb`
  ```ruby
  require 'rails_helper'

  RSpec.describe 'Api::V1::Learners', type: :request do
    describe 'POST /api/v1/learners' do
      context 'with valid parameters' do
        let(:valid_params) do
          {
            learner: {
              employee_id: 'EMP123',
              email: 'john@bmo.com',
              first_name: 'John',
              last_name: 'Doe',
              role: 'sales_associate',
              preferred_channel: 'slack'
            }
          }
        end

        it 'creates a new learner' do
          expect {
            post '/api/v1/learners', params: valid_params
          }.to change(Learner, :count).by(1)

          expect(response).to have_http_status(:created)
        end
      end
    end
  end
  ```

**Validation**: `rspec spec/requests` passes with >80% coverage

## Phase 3 Checklist Summary

### Domain Models
- [ ] Learner model with validations and associations
- [ ] LearningPath model with progress tracking
- [ ] Microlesson model with quiz functionality
- [ ] AssessmentResult model with scoring
- [ ] EngagementMetric model for analytics

### Services (Functional)
- [ ] ApplicationService base with dry-monads
- [ ] Learner registration service (Railway Oriented Programming)
- [ ] Lesson generation service
- [ ] All services return Result monads

### AI Integration
- [ ] AI service client with Faraday
- [ ] Circuit breaker pattern (Circuitbox)
- [ ] Retry logic and error handling
- [ ] VCR cassettes for testing

### Multi-Channel Delivery
- [ ] Base channel interface
- [ ] Slack channel (slack-ruby-client)
- [ ] SMS channel (Twilio)
- [ ] Email channel (ActionMailer)
- [ ] Router for channel selection

### Background Jobs
- [ ] Sidekiq configured
- [ ] DailyLessonDispatchJob (scheduled)
- [ ] LessonDeliveryJob with retry logic
- [ ] EngagementMetricsAggregationJob

### API
- [ ] Authentication middleware (JWT)
- [ ] Learners endpoints
- [ ] Learning paths endpoints
- [ ] Assessments endpoints
- [ ] JSON:API serializers

### Security
- [ ] Rate limiting (Rack::Attack)
- [ ] CORS configuration
- [ ] JWT authentication
- [ ] Input validation (dry-validation)

### Testing
- [ ] RSpec configured with SimpleCov
- [ ] Model specs (>80% coverage)
- [ ] Service specs with dry-monads
- [ ] Request specs for all endpoints
- [ ] Job specs with ActiveJob::TestHelper
- [ ] FactoryBot factories
- [ ] VCR for external API calls

## Handoff Criteria
- [ ] `rails db:migrate` completes successfully
- [ ] `rspec` passes with >80% coverage
- [ ] `rails s` starts on port 3001
- [ ] Sidekiq starts and processes jobs
- [ ] API endpoints respond with proper auth
- [ ] Circuit breaker prevents cascading failures
- [ ] Multi-channel delivery works (Slack, SMS, Email)

## Next Phase
Proceed to **[Phase 4: ML Pipeline & Analytics](./04-ml-analytics.md)** to add predictive analytics.

---

**Estimated Time**: 10-12 days
**Complexity**: High
**Key Learning**: Railway Oriented Programming, Circuit Breakers, Multi-Channel Delivery
**Dependencies**: Phase 2 (LangChain service running)
