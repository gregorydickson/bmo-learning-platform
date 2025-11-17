# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

BMO Learning Platform - An enterprise-grade AI-powered microlearning system built with LangChain and Rails. This is a dual-service architecture demonstrating production LangChain patterns, Constitutional AI safety, and multi-channel delivery.

**Core Stack:**
- Python AI Service (FastAPI, LangChain 1.0.7, port 8000)
- Rails API (Rails 7.2.3, port 3000)
- PostgreSQL 16 + pgvector
- Redis 7 (caching, job queue)
- Chroma 0.5.23 (vector store)

---

## Development Commands

### Initial Setup

```bash
# Copy environment variables
cp .env.example .env
# Edit .env and add OPENAI_API_KEY (required)

# Setup script (installs dependencies, creates databases)
./scripts/dev-setup.sh

# Start all services via Docker Compose
docker-compose up

# Or run in background
docker-compose up -d
```

### Python AI Service (app/ai_service)

```bash
cd app/ai_service

# Install dependencies (uses uv for fast package management)
uv sync

# Run tests with coverage (>80% required)
uv run pytest --cov

# Run specific test file
uv run pytest tests/test_lesson_generator.py

# Run specific test
uv run pytest tests/test_lesson_generator.py::test_generate_lesson

# Linting and formatting
uv run black .
uv run ruff check .
uv run mypy .

# Start service locally (auto-reload enabled)
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Interactive API docs
# http://localhost:8000/docs
```

### Rails API (app/rails_api)

```bash
cd app/rails_api

# Install dependencies
bundle install

# Database setup
bundle exec rails db:create
bundle exec rails db:migrate
bundle exec rails db:seed

# Run tests (RSpec, >80% coverage required)
bundle exec rspec

# Run specific test file
bundle exec rspec spec/services/learner_service_spec.rb

# Run specific test
bundle exec rspec spec/services/learner_service_spec.rb:42

# Linting
bundle exec rubocop
bundle exec rubocop -a  # Auto-fix

# Start Rails server
bundle exec rails s -p 3000

# Start Sidekiq (background jobs)
bundle exec sidekiq -C config/sidekiq.yml

# Database migrations
bundle exec rails db:migrate
bundle exec rails db:rollback
bundle exec rails g migration AddFieldToModel

# Rails console
bundle exec rails c
```

### Docker Compose Operations

```bash
# View logs
docker-compose logs -f ai_service
docker-compose logs -f rails_api
docker-compose logs -f sidekiq

# Rebuild services after dependency changes
docker-compose build ai_service
docker-compose build rails_api

# Run migrations in Docker
docker-compose exec rails_api bundle exec rails db:migrate

# Access Rails console in Docker
docker-compose exec rails_api bundle exec rails c

# Access Python shell in Docker
docker-compose exec ai_service uv run python
```

### Terraform Deployment (AWS us-east-2)

```bash
cd infrastructure/terraform/environments/prod

# Initialize (first time only)
terraform init

# Format and validate
terraform fmt
terraform validate

# Plan changes
terraform plan -out=tfplan

# Apply changes
terraform apply tfplan

# View outputs
terraform output
terraform output alb_dns_name

# Destroy infrastructure (WARNING: deletes everything)
terraform destroy
```

**Important**: See `TERRAFORM-DEPLOYMENT-GUIDE.md` for full deployment steps including Docker image builds and OpenAI API key setup.

---

## Architecture Overview

### Service Communication Flow

```
External (Slack/SMS/Email)
    ↓
Rails API (Port 3000) - Business logic, learner management
    ↓ HTTP
Python AI Service (Port 8000) - LangChain, RAG, lesson generation
    ↓
PostgreSQL (learner data) + Chroma (embeddings) + Redis (cache)
```

**Key Architectural Principles:**

1. **Rails API is the orchestrator** - Handles HTTP requests, authentication, learner management, job scheduling
2. **Python AI Service is stateless** - Pure function service for LLM operations, no database writes
3. **Sidekiq handles async work** - Background jobs for delivery (SMS, Slack, email)
4. **Redis caching is critical** - 60%+ cache hit rate reduces LLM costs significantly
5. **pgvector in PostgreSQL** - Can replace Chroma for production if needed

### Two-Service Architecture Rationale

**Why Rails + Python instead of monolithic?**

- **Python/LangChain**: Best-in-class LLM orchestration, rich ecosystem for RAG/agents/chains
- **Rails**: Mature business logic framework, excellent for CRUD, background jobs, integrations
- **Separation of concerns**: AI generation logic isolated from business rules
- **Independent scaling**: Scale AI service separately based on LLM load

### Data Flow for Lesson Generation

1. Rails API receives request: `POST /api/v1/learners/:id/request_lesson`
2. Rails enqueues Sidekiq job: `LessonGenerationJob`
3. Sidekiq calls Python AI Service: `POST http://ai_service:8000/api/v1/generate-lesson`
4. Python AI Service:
   - Retrieves relevant docs from Chroma (RAG)
   - Checks Redis cache for similar queries
   - Generates lesson via LangChain LCEL chain (GPT-4)
   - Validates safety (Constitutional AI, PII detection, content moderation)
   - Returns JSON response
5. Rails receives lesson, saves to PostgreSQL
6. Rails delivers via channel (Slack API, Twilio SMS, email)

### Critical LangChain Patterns Used

**RAG Pipeline** (`app/ai_service/ingestion/vector_store.py`):
- Document loading via LangChain loaders (PDFLoader, TextLoader)
- Text splitting with RecursiveCharacterTextSplitter (chunk_size=1000, overlap=200)
- Embeddings: OpenAI text-embedding-3-small
- Storage: Chroma vector store with persistence

**LCEL Chains** (`app/ai_service/generators/lesson_generator.py`):
- Multi-stage chains: retrieval → generation → validation
- Prompt templates with few-shot examples
- Pydantic v2 output parsers for structured responses
- Retry logic with exponential backoff

**Safety Layer** (`app/ai_service/safety/safety_validator.py`):
- Constitutional AI principles (LangChain 1.0 pattern)
- PII detection regex patterns (SSN, credit cards, emails, phones)
- OpenAI Moderation API integration
- Three-layer validation: input sanitization → generation → output validation

**Caching Strategy** (`app/ai_service/utils/caching.py`):
- Redis-backed LLM cache (semantic similarity hashing)
- TTL: 3600 seconds (1 hour)
- Cache key: hash(topic + difficulty + learner_context)
- Invalidation: manual or TTL expiration

---

## Terraform Infrastructure

The `infrastructure/terraform` directory contains **production-ready AWS deployment** code.

### Module Structure

All infrastructure is modularized for reusability:

```
infrastructure/terraform/
├── modules/
│   ├── vpc/              # VPC, subnets, NAT gateways (3 AZs)
│   ├── security_groups/  # ALB, ECS, RDS, Redis security groups
│   ├── iam/              # ECS task execution/task roles
│   ├── rds/              # PostgreSQL 16 Multi-AZ with pgvector
│   ├── elasticache/      # Redis 7.1 cluster
│   ├── ecr/              # Docker image repositories
│   ├── alb/              # Application Load Balancer with path routing
│   ├── secrets/          # AWS Secrets Manager for credentials
│   ├── ecs/              # ECS Fargate cluster
│   ├── ecs_services/     # Task definitions + services for 3 apps
│   └── s3/               # Documents and backups buckets
└── environments/
    └── prod/
        ├── main.tf           # Integrates all modules
        └── terraform.tfvars  # Production configuration
```

### Critical Terraform Details

**Module Dependencies (order matters):**
1. VPC (independent)
2. Security Groups (depends on VPC)
3. RDS + ElastiCache (depend on VPC, security groups)
4. Secrets (depends on RDS, ElastiCache for connection strings)
5. IAM (depends on Secrets for ARNs)
6. ECR (independent - create first for image pushing)
7. ALB (depends on VPC, security groups)
8. ECS cluster (depends on VPC)
9. ECS services (depends on everything above)

**State Management:**
- Backend: S3 bucket `bmo-learning-terraform-state` (must exist before `terraform init`)
- Lock: DynamoDB table `terraform-state-lock`
- State file: `s3://bmo-learning-terraform-state/prod/terraform.tfstate`

**Image Placeholder Pattern:**
- Variables `ai_service_image` and `rails_api_image` default to `PLACEHOLDER_*`
- **Must update terraform.tfvars** with actual ECR image URIs before deploying ECS services
- Format: `<account-id>.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/ai-service:latest`

**Secrets Manager Critical Setup:**
- Module creates secret **placeholders** but OpenAI API key **must be set manually**:
  ```bash
  aws secretsmanager put-secret-value \
    --secret-id bmo-learning/prod/openai-api-key \
    --secret-string "sk-actual-key" \
    --region us-east-2
  ```
- After setting secret, force ECS service redeployment to pick it up

**ECS Service Inter-Communication:**
- Rails → AI Service: Uses internal ALB (not public DNS)
- Environment variable: `AI_SERVICE_URL=http://localhost:8000` (service discovery)
- Security groups allow inter-service communication

---

## Key Files and Locations

### Configuration
- `.env` - Local development environment variables (gitignored, copy from `.env.example`)
- `app/ai_service/config/settings.py` - Python service configuration (Pydantic settings)
- `app/rails_api/config/application.rb` - Rails configuration
- `app/rails_api/config/database.yml` - Database configuration
- `docker-compose.yml` - Local development orchestration

### Python AI Service Entry Points
- `app/ai_service/app/main.py` - FastAPI application entry point
- `app/ai_service/app/api/routes.py` - API endpoint definitions
- `app/ai_service/generators/lesson_generator.py` - Core LangChain lesson generation
- `app/ai_service/safety/safety_validator.py` - Constitutional AI safety validation

### Rails API Entry Points
- `app/rails_api/config/routes.rb` - API routes
- `app/rails_api/app/controllers/api/v1/*` - REST controllers
- `app/rails_api/app/services/*` - Business logic layer (functional service objects)
- `app/rails_api/app/jobs/*` - Sidekiq background jobs
- `app/rails_api/app/models/*` - ActiveRecord models

### Deployment Guides
- `TERRAFORM-DEPLOYMENT-GUIDE.md` - Complete 5-phase AWS deployment guide
- `DEPLOYMENT-READINESS.md` - Pre-deployment checklist and infrastructure gaps
- `infrastructure/terraform/environments/prod/main.tf` - Production infrastructure definition

---

## Development Workflow Patterns

### Adding a New LangChain Pattern

1. Create implementation in `app/ai_service/` under appropriate subdirectory
2. Add tests in `app/ai_service/tests/test_<pattern>.py`
3. Add route in `app/ai_service/app/api/routes.py` if exposing as API
4. Update `app/ai_service/config/settings.py` if new config needed
5. Run tests: `cd app/ai_service && uv run pytest --cov`
6. Document pattern usage in code with docstrings

### Adding a New Rails API Endpoint

1. Define route in `app/rails_api/config/routes.rb`
2. Create controller in `app/rails_api/app/controllers/api/v1/`
3. Create service object in `app/rails_api/app/services/` (keep controllers thin)
4. Add model if needed in `app/rails_api/app/models/`
5. Write specs in `app/rails_api/spec/`
6. Run tests: `cd app/rails_api && bundle exec rspec`

### Service Communication Pattern (Rails → Python)

**Always use service objects, never call HTTP directly in controllers:**

```ruby
# app/rails_api/app/services/lesson_generation_service.rb
class LessonGenerationService
  include Dry::Monads[:result]

  def call(learner_id:, topic:)
    response = HTTParty.post(
      "#{ENV['AI_SERVICE_URL']}/api/v1/generate-lesson",
      body: { learner_id: learner_id, topic: topic }.to_json,
      headers: { 'Content-Type' => 'application/json' }
    )

    # Handle response with Dry::Monads
    if response.success?
      Success(response.parsed_response)
    else
      Failure(response.body)
    end
  end
end
```

### Database Migration Pattern

**Rails migrations should be reversible:**

```ruby
class AddEngagementScoreToLearners < ActiveRecord::Migration[7.2]
  def change
    add_column :learners, :engagement_score, :decimal, precision: 5, scale: 2
    add_index :learners, :engagement_score
  end
end
```

Run: `bundle exec rails db:migrate`
Rollback: `bundle exec rails db:rollback`

---

## Testing Standards

### Python AI Service

- **Coverage requirement**: >80%
- **Test structure**: Arrange-Act-Assert pattern
- **Mocking**: Use `pytest` fixtures and `unittest.mock` for external services
- **LLM testing**: Mock OpenAI API calls (never call real API in tests)
- **Async tests**: Use `pytest-asyncio` for async functions

### Rails API

- **Coverage requirement**: >80%
- **Test framework**: RSpec with `shoulda-matchers` for model tests
- **Factory pattern**: Use `factory_bot_rails` for test data
- **External API mocking**: Use `webmock` and `vcr` for HTTP mocking
- **Database**: Tests use separate `test` database with `database_cleaner`

---

## Important Environment Variables

### Required (Application Will Not Start Without These)

- `OPENAI_API_KEY` - OpenAI API key for LLM and embeddings
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string

### Optional (For Full Functionality)

- `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` - SMS delivery
- `SLACK_BOT_TOKEN` - Slack message delivery
- `LANGCHAIN_TRACING_V2` / `LANGCHAIN_API_KEY` - LangSmith observability

### Production (AWS Deployment)

All secrets stored in AWS Secrets Manager, injected into ECS tasks via `secrets` block in task definition.

---

## Common Gotchas

### Python Service

1. **Chroma persistence directory**: Ensure `./data/chroma` is writable, or embeddings won't persist
2. **uv lock file**: Run `uv sync` after adding dependencies to update `uv.lock`
3. **Pydantic v2**: Use Pydantic v2 syntax (different from v1), especially for `model_config`
4. **LangChain version**: Using 1.0.7 - some older examples online won't work

### Rails Service

1. **Sidekiq requires Redis**: Ensure Redis is running before starting Sidekiq
2. **Service objects return Dry::Monads**: Always handle `Success()` and `Failure()` cases
3. **Database connection pool**: Default is 5, may need to increase for production
4. **Devise JWT**: Token expiration is 1 hour by default

### Terraform

1. **ECR images must exist**: Can't deploy ECS services without valid Docker images in ECR
2. **OpenAI API key**: Secrets Manager creates empty secret - must set value manually
3. **RDS takes 15+ minutes**: Be patient during `terraform apply`
4. **State bucket must exist first**: Run S3/DynamoDB creation before `terraform init`

---

## Debugging Tips

### AI Service Issues

```bash
# View logs
docker-compose logs -f ai_service

# Check health endpoint
curl http://localhost:8000/health

# Access Python REPL in container
docker-compose exec ai_service uv run python

# Test OpenAI connection
docker-compose exec ai_service uv run python -c "from openai import OpenAI; print(OpenAI().models.list())"
```

### Rails API Issues

```bash
# View logs
docker-compose logs -f rails_api

# Check health endpoint
curl http://localhost:3000/health

# Rails console for debugging
docker-compose exec rails_api bundle exec rails c

# Check database connection
docker-compose exec rails_api bundle exec rails db:version

# View Sidekiq web UI (if enabled)
# http://localhost:3000/sidekiq
```

### Database Issues

```bash
# Connect to PostgreSQL directly
docker-compose exec postgres psql -U postgres -d bmo_learning_dev

# Check if pgvector extension is installed
docker-compose exec postgres psql -U postgres -d bmo_learning_dev -c "SELECT * FROM pg_extension WHERE extname = 'vector';"

# View Redis keys
docker-compose exec redis redis-cli KEYS '*'
```

---

## Pre-commit Hooks

Install to run automatic checks before commits:

```bash
pre-commit install
```

**Hooks include:**
- Black (Python formatting)
- Ruff (Python linting)
- Rubocop (Ruby linting)
- detect-secrets (prevent committing API keys)
- YAML validation
- Large file detection

---

## Cost Awareness

**Local Development:**
- Free (Docker Compose)
- OpenAI API usage only (~$5-10/month for testing)

**Production (AWS):**
- Infrastructure: ~$665/month
- OpenAI API: ~$450-650/month (highly variable based on usage)
- **Critical**: Use Redis caching to reduce LLM calls by 60%+

---

## Documentation Locations

- **Architecture**: `docs/architecture/overview.md`
- **Implementation phases**: `docs/workplans/00-MASTER-WORKPLAN.md`
- **API documentation**: FastAPI auto-docs at `http://localhost:8000/docs`
- **Deployment**: `TERRAFORM-DEPLOYMENT-GUIDE.md`
- **Codebase overview**: `CODEBASE-OVERVIEW.md`

---

**Last Updated**: 2025-11-16
