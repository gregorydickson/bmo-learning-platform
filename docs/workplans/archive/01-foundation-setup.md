# Phase 1: Foundation & Setup

**Duration**: 3-5 days
**Goal**: Create production-ready project scaffold with security, testing, and deployment infrastructure

## Overview
This phase establishes the foundation for all subsequent work. We prioritize:
1. **Security-first configuration** (secrets management, scanning)
2. **Developer experience** (Docker, tooling, pre-commit hooks)
3. **Quality gates** (linting, testing, CI/CD)
4. **Documentation structure** (ADRs, READMEs, diagrams)

## Prerequisites
- [ ] Docker Desktop installed and running
- [ ] Python 3.11+ installed
- [ ] Ruby 3.2+ installed
- [ ] Node.js 20+ installed (for tooling)
- [ ] Git configured
- [ ] OpenAI API key obtained
- [ ] AWS account created (free tier acceptable)

## 1. Project Structure

### 1.1 Create Directory Scaffold
- [ ] Create root-level directories
  ```bash
  mkdir -p {app,infrastructure,ml_pipeline,tests,docs,scripts,.github}
  mkdir -p app/{ai_service,rails_api}
  mkdir -p docs/{architecture,security,api,adrs}
  mkdir -p infrastructure/terraform/{modules,environments}
  ```

- [ ] Create Python service structure
  ```bash
  mkdir -p app/ai_service/{ingestion,agents,generators,ml,qa,api,config}
  mkdir -p app/ai_service/{chains,tools,memory,retrievers,callbacks}
  mkdir -p tests/ai_service/{unit,integration,e2e}
  ```

- [ ] Create Rails service structure
  ```bash
  mkdir -p app/rails_api/{app,config,db,spec,lib}
  mkdir -p app/rails_api/app/{models,controllers,services,jobs,channels}
  mkdir -p app/rails_api/spec/{models,requests,services,jobs}
  ```

- [ ] Create ML pipeline structure
  ```bash
  mkdir -p ml_pipeline/{training,evaluation,deployment,data}
  mkdir -p ml_pipeline/models/{engagement_predictor,risk_classifier}
  ```

**Validation**: `tree -L 3 -d` shows expected structure

### 1.2 Initialize Git Repository
- [ ] Initialize git
  ```bash
  git init
  git branch -M main
  ```

- [ ] Create comprehensive `.gitignore`
  ```gitignore
  # Python
  __pycache__/
  *.py[cod]
  *$py.class
  .Python
  venv/
  .pytest_cache/
  .coverage
  htmlcov/

  # Ruby
  *.gem
  *.rbc
  .bundle/
  vendor/bundle/
  .byebug_history

  # Environment
  .env
  .env.*
  !.env.example

  # Secrets
  **/secrets.yml
  **/*secret*
  **/*credentials*
  !config/credentials.yml.enc

  # IDE
  .vscode/
  .idea/
  *.swp
  *.swo

  # OS
  .DS_Store
  Thumbs.db

  # Docker
  .docker/data/

  # Terraform
  **/.terraform/
  *.tfstate
  *.tfstate.backup
  .terraform.lock.hcl

  # ML
  ml_pipeline/data/raw/
  ml_pipeline/models/artifacts/
  *.h5
  *.pkl

  # Logs
  logs/
  *.log
  ```

- [ ] Create `.env.example` template
  ```bash
  # OpenAI
  OPENAI_API_KEY=sk-...
  OPENAI_MODEL=gpt-4-turbo-preview

  # Database
  DATABASE_URL=postgresql://localhost:5432/bmo_learning_dev
  REDIS_URL=redis://localhost:6379/0

  # AWS (for local testing)
  AWS_ACCESS_KEY_ID=
  AWS_SECRET_ACCESS_KEY=
  AWS_REGION=us-east-1

  # External Services
  TWILIO_ACCOUNT_SID=
  TWILIO_AUTH_TOKEN=
  SLACK_BOT_TOKEN=

  # Application
  RAILS_ENV=development
  PYTHON_ENV=development
  LOG_LEVEL=INFO
  ```

**Validation**: `.gitignore` prevents secrets from being committed

## 2. Dependency Management

### 2.1 Python Dependencies
- [ ] Create `app/ai_service/pyproject.toml` (using uv)
  ```toml
  [project]
  name = "bmo-learning-ai"
  version = "0.1.0"
  description = "AI service for BMO microlearning platform"
  requires-python = ">=3.11"

  dependencies = [
      # LangChain Core (Latest stable versions - Nov 2025)
      "langchain==1.0.7",
      "langchain-core==1.0.4",
      "langchain-openai==1.0.3",
      "langchain-community==0.4.1",

      # Vector Stores
      "chromadb==0.5.23",
      "pgvector>=0.2.4",

      # Document Loaders
      "pypdf>=4.0.0",
      "unstructured>=0.12.0",

      # ML & Data
      "numpy>=1.26.0",
      "pandas>=2.1.0",
      "scikit-learn>=1.4.0",
      "xgboost>=2.0.0",

      # API & Web
      "fastapi==0.121.2",
      "uvicorn==0.34.0",
      "httpx==0.28.1",

      # Database
      "psycopg2-binary==2.9.9",
      "sqlalchemy>=2.0.0",
      "redis==5.2.1",

      # OpenAI
      "openai==2.8.0",

      # Utilities
      "pydantic==2.12.4",
      "pydantic-settings==2.7.1",
      "python-dotenv>=1.0.0",
      "structlog>=24.1.0",
  ]

  [project.optional-dependencies]
  dev = [
      "pytest>=8.0.0",
      "pytest-cov>=4.1.0",
      "pytest-asyncio>=0.23.0",
      "black>=24.0.0",
      "ruff>=0.1.0",
      "mypy>=1.8.0",
      "pre-commit>=3.6.0",
  ]

  [tool.black]
  line-length = 100
  target-version = ['py311']

  [tool.ruff]
  line-length = 100
  target-version = "py311"
  select = ["E", "F", "I", "N", "W", "B", "SIM"]

  [tool.mypy]
  python_version = "3.11"
  strict = true
  warn_return_any = true
  warn_unused_configs = true

  [tool.pytest.ini_options]
  testpaths = ["tests"]
  python_files = "test_*.py"
  python_functions = "test_*"
  addopts = "-v --cov=app/ai_service --cov-report=html --cov-report=term"
  ```

- [ ] Install Python dependencies
  ```bash
  cd app/ai_service
  uv sync --all-extras
  ```

**Validation**: `uv run python -c "import langchain; print(langchain.__version__)"`

### 2.2 Rails Dependencies
- [ ] Initialize Rails app with API mode
  ```bash
  cd app/rails_api
  gem install rails -v 7.2.3
  rails new . --api --database=postgresql --skip-test
  ```

- [ ] Add gems to `Gemfile`
  ```ruby
  # Gemfile
  source 'https://rubygems.org'
  ruby '~> 3.2.0'

  gem 'rails', '~> 7.2.3'
  gem 'pg', '~> 1.5'
  gem 'puma', '~> 6.4'

  # Redis & Background Jobs
  gem 'redis', '~> 5.3'
  gem 'sidekiq', '~> 7.3'

  # API & Serialization
  gem 'blueprinter', '~> 1.0'
  gem 'rack-cors', '~> 2.0'
  gem 'jbuilder', '~> 2.11'

  # Authentication & Security
  gem 'devise', '~> 4.9'
  gem 'devise-jwt', '~> 0.11'
  gem 'pundit', '~> 2.3'
  gem 'brakeman', '~> 6.1'

  # External Services
  gem 'httparty', '~> 0.21'
  gem 'twilio-ruby', '~> 6.9'
  gem 'slack-ruby-client', '~> 2.2'

  # Utilities
  gem 'dry-monads', '~> 1.6'
  gem 'dry-validation', '~> 1.10'

  group :development, :test do
    gem 'rspec-rails', '~> 6.1'
    gem 'factory_bot_rails', '~> 6.4'
    gem 'faker', '~> 3.2'
    gem 'pry-byebug', '~> 3.10'
    gem 'rubocop', '~> 1.60'
    gem 'rubocop-rails', '~> 2.23'
    gem 'rubocop-rspec', '~> 2.26'
  end

  group :test do
    gem 'shoulda-matchers', '~> 6.1'
    gem 'simplecov', '~> 0.22'
    gem 'webmock', '~> 3.20'
    gem 'vcr', '~> 6.2'
  end
  ```

- [ ] Install Rails dependencies
  ```bash
  bundle install
  ```

**Validation**: `bundle exec rails -v` shows Rails 7.2.3

### 2.3 Node.js Tooling (Optional)
- [ ] Create `package.json` for development tools
  ```json
  {
    "name": "bmo-learning-platform",
    "version": "0.1.0",
    "private": true,
    "scripts": {
      "lint": "eslint . --ext .js,.ts",
      "format": "prettier --write ."
    },
    "devDependencies": {
      "prettier": "^3.2.0",
      "markdownlint-cli": "^0.39.0"
    }
  }
  ```

**Validation**: Optional - only if using Node tooling

## 3. Docker Configuration

### 3.1 Python Service Dockerfile
- [ ] Create `app/ai_service/Dockerfile`
  ```dockerfile
  FROM python:3.11-slim as base

  # Security: Run as non-root user
  RUN useradd -m -u 1000 appuser

  WORKDIR /app

  # Install system dependencies
  RUN apt-get update && apt-get install -y \
      gcc \
      g++ \
      && rm -rf /var/lib/apt/lists/*

  # Install uv for dependency management
  RUN pip install uv

  # Copy dependency files
  COPY pyproject.toml ./
  COPY uv.lock* ./

  # Install dependencies (make uv.lock optional)
  RUN if [ -f uv.lock ]; then uv sync --frozen; else uv sync; fi

  # Copy application code
  COPY . .

  # Switch to non-root user
  USER appuser

  # Expose port
  EXPOSE 8000

  # Health check
  HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

  # Run application
  CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
  ```

### 3.2 Rails Service Dockerfile
- [ ] Create `app/rails_api/Dockerfile`
  ```dockerfile
  FROM ruby:3.2.2-slim as base

  # Security: Run as non-root user
  RUN useradd -m -u 1000 appuser

  WORKDIR /app

  # Install dependencies (including curl for health checks)
  RUN apt-get update && apt-get install -y \
      build-essential \
      libpq-dev \
      nodejs \
      curl \
      && rm -rf /var/lib/apt/lists/*

  # Install gems
  COPY Gemfile Gemfile.lock ./
  RUN bundle install

  # Copy application code
  COPY . .

  # Precompile assets (if needed)
  # RUN bundle exec rails assets:precompile

  # Switch to non-root user
  RUN chown -R appuser:appuser /app
  USER appuser

  # Expose port
  EXPOSE 3000

  # Health check
  HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

  # Run application
  CMD ["bundle", "exec", "puma", "-C", "config/puma.rb"]
  ```

### 3.3 Docker Compose Configuration
- [ ] Create `docker-compose.yml`
  ```yaml
  version: '3.9'

  services:
    # PostgreSQL with pgvector
    postgres:
      image: ankane/pgvector:latest
      environment:
        POSTGRES_USER: postgres
        POSTGRES_PASSWORD: postgres
        POSTGRES_DB: bmo_learning_dev
      ports:
        - "5432:5432"
      volumes:
        - postgres_data:/var/lib/postgresql/data
      healthcheck:
        test: ["CMD-SHELL", "pg_isready -U postgres"]
        interval: 10s
        timeout: 5s
        retries: 5

    # Redis
    redis:
      image: redis:7-alpine
      ports:
        - "6379:6379"
      volumes:
        - redis_data:/data
      healthcheck:
        test: ["CMD", "redis-cli", "ping"]
        interval: 10s
        timeout: 3s
        retries: 5

    # Python AI Service
    ai_service:
      build:
        context: ./app/ai_service
        dockerfile: Dockerfile
      environment:
        - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/bmo_learning_dev
        - REDIS_URL=redis://redis:6379/0
        - OPENAI_API_KEY=${OPENAI_API_KEY}
      env_file:
        - .env
      ports:
        - "8000:8000"
      volumes:
        - ./app/ai_service:/app
        - ai_service_cache:/app/.cache
      depends_on:
        postgres:
          condition: service_healthy
        redis:
          condition: service_healthy
      command: uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

    # Rails API Service
    rails_api:
      build:
        context: ./app/rails_api
        dockerfile: Dockerfile
      environment:
        - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/bmo_learning_dev
        - REDIS_URL=redis://redis:6379/0
        - AI_SERVICE_URL=http://ai_service:8000
      env_file:
        - .env
      ports:
        - "3000:3000"
      volumes:
        - ./app/rails_api:/app
        - rails_bundle:/usr/local/bundle
      depends_on:
        postgres:
          condition: service_healthy
        redis:
          condition: service_healthy
      command: bundle exec puma -C config/puma.rb

    # Sidekiq (Background Jobs)
    sidekiq:
      build:
        context: ./app/rails_api
        dockerfile: Dockerfile
      environment:
        - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/bmo_learning_dev
        - REDIS_URL=redis://redis:6379/0
      env_file:
        - .env
      volumes:
        - ./app/rails_api:/app
        - rails_bundle:/usr/local/bundle
      depends_on:
        postgres:
          condition: service_healthy
        redis:
          condition: service_healthy
      command: bundle exec sidekiq -C config/sidekiq.yml

  volumes:
    postgres_data:
    redis_data:
    ai_service_cache:
    rails_bundle:
  ```

- [ ] Create `docker-compose.test.yml` for testing
  ```yaml
  version: '3.9'

  services:
    postgres_test:
      image: ankane/pgvector:latest
      environment:
        POSTGRES_USER: postgres
        POSTGRES_PASSWORD: postgres
        POSTGRES_DB: bmo_learning_test
      tmpfs:
        - /var/lib/postgresql/data

    ai_service_test:
      build:
        context: ./app/ai_service
        dockerfile: Dockerfile
      environment:
        - DATABASE_URL=postgresql://postgres:postgres@postgres_test:5432/bmo_learning_test
        - TESTING=true
      depends_on:
        - postgres_test
      command: uv run pytest
  ```

**Validation**: `docker-compose config` validates syntax

## 4. Development Tooling

### 4.1 Pre-commit Hooks
- [ ] Create `.pre-commit-config.yaml`
  ```yaml
  repos:
    # Python
    - repo: https://github.com/psf/black
      rev: 24.1.1
      hooks:
        - id: black
          files: ^app/ai_service/

    - repo: https://github.com/astral-sh/ruff-pre-commit
      rev: v0.1.15
      hooks:
        - id: ruff
          files: ^app/ai_service/
          args: [--fix]

    - repo: https://github.com/pre-commit/mirrors-mypy
      rev: v1.8.0
      hooks:
        - id: mypy
          files: ^app/ai_service/
          additional_dependencies: [types-all]

    # Ruby
    - repo: https://github.com/rubocop/rubocop
      rev: v1.60.0
      hooks:
        - id: rubocop
          files: ^app/rails_api/

    # General
    - repo: https://github.com/pre-commit/pre-commit-hooks
      rev: v4.5.0
      hooks:
        - id: trailing-whitespace
        - id: end-of-file-fixer
        - id: check-yaml
        - id: check-added-large-files
          args: [--maxkb=500]
        - id: check-merge-conflict
        - id: detect-private-key

    # Security
    - repo: https://github.com/Yelp/detect-secrets
      rev: v1.4.0
      hooks:
        - id: detect-secrets
          args: ['--baseline', '.secrets.baseline']
  ```

- [ ] Install pre-commit
  ```bash
  pip install pre-commit
  pre-commit install
  pre-commit run --all-files  # Initial run
  ```

**Validation**: Pre-commit hooks run on `git commit`

### 4.2 EditorConfig
- [ ] Create `.editorconfig`
  ```ini
  root = true

  [*]
  charset = utf-8
  end_of_line = lf
  insert_final_newline = true
  trim_trailing_whitespace = true

  [*.{py,rb}]
  indent_style = space
  indent_size = 4

  [*.{yml,yaml,json}]
  indent_style = space
  indent_size = 2

  [Makefile]
  indent_style = tab
  ```

### 4.3 Development Scripts
- [ ] Create `scripts/dev-setup.sh`
  ```bash
  #!/bin/bash
  set -e

  echo "Setting up development environment..."

  # Check prerequisites
  command -v docker >/dev/null 2>&1 || { echo "Docker is required"; exit 1; }
  command -v python3 >/dev/null 2>&1 || { echo "Python 3.11+ is required"; exit 1; }
  command -v ruby >/dev/null 2>&1 || { echo "Ruby 3.2+ is required"; exit 1; }

  # Copy environment template
  if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file - please update with your credentials"
  fi

  # Install Python dependencies
  echo "Installing Python dependencies..."
  cd app/ai_service
  uv sync --all-extras
  cd ../..

  # Install Rails dependencies
  echo "Installing Rails dependencies..."
  cd app/rails_api
  bundle install
  cd ../..

  # Setup pre-commit hooks
  echo "Setting up pre-commit hooks..."
  pre-commit install

  # Start services
  echo "Starting Docker services..."
  docker-compose up -d postgres redis

  # Wait for databases
  echo "Waiting for databases..."
  sleep 5

  # Setup databases
  echo "Setting up databases..."
  cd app/rails_api
  bundle exec rails db:create db:migrate
  cd ../..

  echo "Setup complete! Run 'docker-compose up' to start all services."
  ```

- [ ] Make script executable
  ```bash
  chmod +x scripts/dev-setup.sh
  ```

**Validation**: `./scripts/dev-setup.sh` runs without errors

## 5. CI/CD Pipeline

### 5.1 GitHub Actions - Python Tests
- [ ] Create `.github/workflows/python-tests.yml`
  ```yaml
  name: Python Tests

  on:
    push:
      branches: [main, develop]
      paths:
        - 'app/ai_service/**'
    pull_request:
      branches: [main, develop]
      paths:
        - 'app/ai_service/**'

  jobs:
    test:
      runs-on: ubuntu-latest

      services:
        postgres:
          image: ankane/pgvector:latest
          env:
            POSTGRES_USER: postgres
            POSTGRES_PASSWORD: postgres
            POSTGRES_DB: test_db
          options: >-
            --health-cmd pg_isready
            --health-interval 10s
            --health-timeout 5s
            --health-retries 5
          ports:
            - 5432:5432

      steps:
        - uses: actions/checkout@v4

        - name: Set up Python
          uses: actions/setup-python@v5
          with:
            python-version: '3.11'

        - name: Install uv
          run: pip install uv

        - name: Install dependencies
          working-directory: app/ai_service
          run: uv sync --all-extras

        - name: Run linting
          working-directory: app/ai_service
          run: |
            uv run ruff check .
            uv run black --check .
            uv run mypy .

        - name: Run tests
          working-directory: app/ai_service
          env:
            DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
          run: uv run pytest --cov --cov-report=xml

        - name: Upload coverage
          uses: codecov/codecov-action@v3
          with:
            files: ./app/ai_service/coverage.xml
  ```

### 5.2 GitHub Actions - Rails Tests
- [ ] Create `.github/workflows/rails-tests.yml`
  ```yaml
  name: Rails Tests

  on:
    push:
      branches: [main, develop]
      paths:
        - 'app/rails_api/**'
    pull_request:
      branches: [main, develop]
      paths:
        - 'app/rails_api/**'

  jobs:
    test:
      runs-on: ubuntu-latest

      services:
        postgres:
          image: postgres:16
          env:
            POSTGRES_USER: postgres
            POSTGRES_PASSWORD: postgres
          options: >-
            --health-cmd pg_isready
            --health-interval 10s
            --health-timeout 5s
            --health-retries 5
          ports:
            - 5432:5432

        redis:
          image: redis:7-alpine
          options: >-
            --health-cmd "redis-cli ping"
            --health-interval 10s
            --health-timeout 5s
            --health-retries 5
          ports:
            - 6379:6379

      steps:
        - uses: actions/checkout@v4

        - name: Set up Ruby
          uses: ruby/setup-ruby@v1
          with:
            ruby-version: '3.2.2'
            bundler-cache: true
            working-directory: app/rails_api

        - name: Run linting
          working-directory: app/rails_api
          run: bundle exec rubocop

        - name: Run security scan
          working-directory: app/rails_api
          run: bundle exec brakeman -q

        - name: Setup database
          working-directory: app/rails_api
          env:
            DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
            RAILS_ENV: test
          run: |
            bundle exec rails db:create
            bundle exec rails db:migrate

        - name: Run tests
          working-directory: app/rails_api
          env:
            DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
            RAILS_ENV: test
          run: bundle exec rspec --format documentation

        - name: Upload coverage
          uses: codecov/codecov-action@v3
          with:
            files: ./app/rails_api/coverage/coverage.xml
  ```

### 5.3 GitHub Actions - Security Scan
- [ ] Create `.github/workflows/security.yml`
  ```yaml
  name: Security Scan

  on:
    push:
      branches: [main, develop]
    pull_request:
      branches: [main, develop]
    schedule:
      - cron: '0 0 * * 0'  # Weekly

  jobs:
    dependency-scan:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4

        - name: Run Trivy vulnerability scanner
          uses: aquasecurity/trivy-action@master
          with:
            scan-type: 'fs'
            scan-ref: '.'
            format: 'sarif'
            output: 'trivy-results.sarif'

        - name: Upload Trivy results to GitHub Security
          uses: github/codeql-action/upload-sarif@v2
          with:
            sarif_file: 'trivy-results.sarif'

    secret-scan:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4

        - name: Gitleaks scan
          uses: gitleaks/gitleaks-action@v2
          env:
            GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  ```

**Validation**: Push to GitHub triggers workflows

## 6. Documentation

### 6.1 Project README
- [ ] Create comprehensive `README.md`
  ```markdown
  # BMO Business Credit Card Training Platform

  A microlearning platform demonstrating production LangChain implementation.

  ## Quick Start

  ### Prerequisites
  - Docker Desktop
  - Python 3.11+
  - Ruby 3.2+
  - OpenAI API key

  ### Setup
  ```bash
  # Clone repository
  git clone <repo-url>
  cd learning-app

  # Run setup script
  ./scripts/dev-setup.sh

  # Start services
  docker-compose up
  ```

  ## Architecture
  See [docs/architecture/overview.md](docs/architecture/overview.md)

  ## API Documentation
  - Python AI Service: http://localhost:8000/docs
  - Rails API: http://localhost:3000/api/docs

  ## Testing
  ```bash
  # Python tests
  cd app/ai_service && uv run pytest

  # Rails tests
  cd app/rails_api && bundle exec rspec
  ```

  ## License
  MIT
  ```

### 6.2 Architecture Decision Records
- [ ] Create ADR template `docs/adrs/000-template.md`
  ```markdown
  # ADR-000: [Title]

  **Date**: YYYY-MM-DD
  **Status**: [Proposed | Accepted | Deprecated | Superseded]

  ## Context
  What is the issue we're facing?

  ## Decision
  What did we decide?

  ## Consequences
  What are the positive and negative outcomes?

  ## Alternatives Considered
  What other options did we evaluate?
  ```

- [ ] Create first ADR for tech stack
  ```markdown
  # ADR-001: Use LangChain for AI Orchestration

  **Date**: 2025-11-15
  **Status**: Accepted

  ## Context
  We need an AI framework for RAG, agents, and content generation.

  ## Decision
  Use LangChain as the primary AI orchestration framework.

  ## Consequences
  **Positive**:
  - Rich ecosystem of tools and integrations
  - Active community and documentation
  - Constitutional AI for safety

  **Negative**:
  - Abstraction complexity
  - Rapid version changes
  - Learning curve for team

  ## Alternatives Considered
  - Haystack: Less mature agent framework
  - LlamaIndex: Better for pure RAG, weaker on agents
  - Custom: Too much development time
  ```

**Validation**: Documentation is clear and comprehensive

## 7. Security Configuration

### 7.1 Secrets Management
- [ ] Create `.secrets.baseline` for detect-secrets
  ```bash
  detect-secrets scan > .secrets.baseline
  ```

- [ ] Configure environment variable validation
  ```python
  # app/ai_service/config/settings.py
  from pydantic_settings import BaseSettings
  from typing import Optional

  class Settings(BaseSettings):
      openai_api_key: str
      database_url: str
      redis_url: str

      class Config:
          env_file = ".env"
          case_sensitive = False

  settings = Settings()
  ```

### 7.2 Security Headers (Rails)
- [ ] Configure `config/application.rb`
  ```ruby
  config.middleware.use Rack::Cors do
    allow do
      origins ENV.fetch("ALLOWED_ORIGINS", "http://localhost:3001").split(",")
      resource "*",
        headers: :any,
        methods: [:get, :post, :put, :patch, :delete, :options],
        credentials: true
    end
  end

  config.middleware.use ActionDispatch::ContentSecurityPolicy::Middleware
  ```

**Validation**: Security scans pass in CI

## 8. Quality Gates

### 8.1 Coverage Requirements
- [ ] Configure coverage thresholds
  ```ini
  # app/ai_service/pytest.ini
  [pytest]
  addopts = --cov --cov-fail-under=80
  ```

- [ ] Configure SimpleCov for Rails
  ```ruby
  # app/rails_api/spec/spec_helper.rb
  require 'simplecov'
  SimpleCov.start 'rails' do
    minimum_coverage 80
  end
  ```

**Validation**: Tests fail if coverage drops below 80%

## Phase 1 Checklist Summary

### Critical Path
- [ ] Project structure created
- [ ] Dependencies installed (Python, Ruby)
- [ ] Docker Compose working
- [ ] Pre-commit hooks active
- [ ] CI/CD pipelines passing
- [ ] Documentation complete

### Quality Gates
- [ ] All linters passing
- [ ] Security scans clean
- [ ] No secrets in repository
- [ ] READMEs comprehensive
- [ ] ADRs documented

### Handoff Criteria
- [ ] `docker-compose up` starts all services
- [ ] `./scripts/dev-setup.sh` runs successfully
- [ ] Tests pass locally and in CI
- [ ] Documentation reviewed
- [ ] Security baseline established

## Next Phase
Proceed to **[Phase 2: LangChain AI Service](./02-langchain-service.md)** once all checklist items are complete.

---

**Estimated Time**: 3-5 days
**Complexity**: Medium
**Blocking Issues**: None expected
**Dependencies**: None - this is the foundation
