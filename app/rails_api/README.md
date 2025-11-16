# BMO Learning Rails API

Rails API service for the BMO microlearning platform.

## Features

- RESTful API endpoints
- Background job processing with Sidekiq
- Multi-channel delivery (Slack, SMS, Email)
- Integration with AI service
- PostgreSQL with pgvector

## Setup

### Prerequisites

- Ruby 3.2+
- PostgreSQL 16+
- Redis

### Installation

```bash
# Install dependencies
bundle install

# Setup database
bundle exec rails db:create db:migrate

# Run tests
bundle exec rspec

# Start server
bundle exec rails server
```

## API Documentation

API endpoints available at http://localhost:3000/api/v1

## Project Structure

```
app/rails_api/
├── app/
│   ├── models/          # Domain models
│   ├── controllers/     # API controllers
│   ├── services/        # Business logic
│   └── jobs/            # Background jobs
├── config/              # Configuration
├── db/                  # Database migrations
└── spec/                # RSpec tests
```

## Testing

```bash
# Run all tests
bundle exec rspec

# Run with coverage
bundle exec rspec --format documentation

# Run specific test
bundle exec rspec spec/models/learner_spec.rb
```

## Background Jobs

```bash
# Start Sidekiq
bundle exec sidekiq -C config/sidekiq.yml
```

## Development

See the main project README and Phase 3 workplan for implementation details.
