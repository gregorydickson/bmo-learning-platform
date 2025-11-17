# BMO Learning Platform - Comprehensive Codebase Overview

**Project**: Enterprise AI-Powered Microlearning Platform
**Status**: Production-Ready (Phases 1-6 Complete)
**Last Updated**: 2025-11-15
**Deployment Target**: AWS us-east-2 region

---

## EXECUTIVE SUMMARY

The BMO Learning Platform is a **full-stack, production-ready microlearning system** demonstrating enterprise LangChain best practices. It delivers AI-powered personalized financial literacy training via multiple channels (Slack, SMS, Email) with a target of **7x higher completion rates** (70% vs industry 10%) and achieves **production-grade LLM safety** through Constitutional AI, PII detection, and content moderation.

**Key Metrics**:
- **100+ files** implementing 6 implementation phases
- **2 primary services** (Python AI + Rails API) 
- **4 databases/stores** (PostgreSQL, Redis, Chroma, S3)
- **3 delivery channels** (Slack, SMS, Email)
- **15+ LangChain patterns** demonstrated
- **Terraform infrastructure** for AWS deployment

---

## 1. APPLICATION ARCHITECTURE

### 1.1 Core Tech Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **API Gateway** | Rails | 7.2.3 | Business logic, workflow orchestration, REST API |
| **AI Orchestration** | LangChain | 1.0.7 | RAG, agents, chains, safety guardrails |
| **AI Framework** | FastAPI | 0.121 | High-performance async Python API |
| **LLM Provider** | OpenAI | GPT-4, text-embedding-3 | Content generation & embeddings |
| **Vector Store** | Chroma | 0.5.23 | Document embeddings & RAG retrieval |
| **Primary Database** | PostgreSQL | 16 + pgvector | Transactional data, vectors |
| **Cache/Queue** | Redis | 7-alpine | Caching, job queue, sessions |
| **Background Jobs** | Sidekiq | 7.3 | Async task processing |
| **ML Models** | XGBoost + scikit-learn | 2.0+ | Engagement prediction, risk classification |
| **Infrastructure** | Terraform | 1.9 | AWS Infrastructure as Code |
| **Containerization** | Docker | latest | Local dev & cloud deployment |

### 1.2 Deployment Model

```
┌─────────────────────────────────────────────────────────────┐
│  AWS ECS Fargate (Production)                               │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │ AI Svc   │    │ Rails    │    │ Sidekiq  │              │
│  │ (Python) │    │ (Ruby)   │    │ Workers  │              │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘              │
│       │               │               │                     │
│       └───────────────┼───────────────┘                     │
│                       │                                     │
│       ┌───────────────┴────────────────┐                   │
│       │                                │                   │
│       ▼                                ▼                   │
│  ┌──────────────┐          ┌──────────────────┐           │
│  │ RDS PostgreSQL          │ ElastiCache Redis│           │
│  │ + pgvector   │          │                  │           │
│  └──────────────┘          └──────────────────┘           │
│                                                            │
│  ┌──────────────────┐      ┌──────────────┐              │
│  │ Chroma Vector DB │      │ S3 (Docs)    │              │
│  │ or pgvector      │      │              │              │
│  └──────────────────┘      └──────────────┘              │
└─────────────────────────────────────────────────────────────┘

Local: Docker Compose (same services)
```

### 1.3 Service Communication

```
External Channels
    (Slack, SMS, Email)
           │
           ▼
    Rails API (3000) ◄──► Python AI Service (8000)
           │               │
           ├──────────────┼────────────────┐
           ▼              ▼                ▼
        PostgreSQL      Redis            Chroma
       (Business)      (Cache)           (RAG)
```

---

## 2. KEY DIRECTORIES & PURPOSES

### 2.1 Root Structure

```
learning-app/
├── .env.example              # Environment configuration template
├── .github/workflows/        # CI/CD pipelines (GitHub Actions)
├── docker-compose.yml        # Local development orchestration
├── docker-compose.test.yml   # Test environment setup
│
├── app/                      # Application services
│   ├── ai_service/          # Python LangChain AI service (PORT 8000)
│   └── rails_api/           # Ruby on Rails API service (PORT 3000)
│
├── infrastructure/           # Infrastructure as Code
│   └── terraform/            # AWS deployment templates
│       ├── modules/          # Reusable Terraform modules
│       │   ├── vpc/         # VPC, subnets, security groups
│       │   └── ecs/         # ECS cluster, tasks, load balancing
│       └── environments/     # Env-specific configs
│           └── prod/        # Production configuration
│
├── ml_pipeline/              # Machine learning components
│   ├── training/            # Model training scripts
│   ├── evaluation/          # Model evaluation & metrics
│   ├── models/              # Trained model artifacts
│   └── deployment/          # ML deployment scripts
│
├── docs/                     # Documentation
│   ├── architecture/        # System design & patterns
│   ├── api/                 # API documentation
│   ├── security/            # Security policies
│   └── workplans/           # Implementation phases
│
├── scripts/                  # Development scripts
│   └── dev-setup.sh         # Bootstrap development environment
│
└── tests/                    # Integration & E2E tests
    └── ai_service/          # AI service test suites
```

---

## 3. SERVICES & COMPONENTS

### 3.1 Python AI Service (`/app/ai_service`)

**Language**: Python 3.11+
**Framework**: FastAPI + LangChain
**Port**: 8000 (development), ECS container (production)

**Directory Structure**:
```
app/ai_service/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── api/
│   │   └── routes.py        # REST API endpoints
│   ├── config/
│   │   └── settings.py      # Pydantic settings, env variables
│   └── utils/
│       └── logging.py       # Structured logging (structlog)
│
├── agents/                  # LangChain agents
│   └── learning_orchestrator.py  # Adaptive learning agent
│
├── chains/                  # LangChain chains
│   └── (chaining logic)
│
├── generators/              # Content generation
│   ├── lesson_generator.py  # LCEL chains for lessons
│   └── few_shot_prompts.py  # Few-shot examples
│
├── ingestion/               # Document processing
│   ├── document_processor.py     # Load PDFs, text files
│   ├── vector_store.py           # ChromaDB management
│   └── chunking.py               # RecursiveCharacterTextSplitter
│
├── retrievers/              # RAG retrieval
│   ├── basic_retriever.py   # Vector similarity search
│   └── multi_query_retriever.py  # Query expansion
│
├── safety/                  # LLM safety layer
│   └── safety_validator.py  # Constitutional AI, PII, moderation
│
├── memory/                  # Conversation memory
├── callbacks/               # LangChain callbacks (monitoring)
├── ml/                      # ML integration
├── tools/                   # Custom LangChain tools
├── qa/                      # Q&A chains
│
├── pyproject.toml           # Python dependencies (uv)
├── Dockerfile               # Container image
└── pytest.ini               # Test configuration
```

**Key Dependencies**:
```toml
# LangChain Ecosystem
langchain==1.0.7
langchain-core==1.0.4
langchain-openai==1.0.3
langchain-community==0.4.1

# Vector Store & Document Processing
chromadb==0.5.23
pypdf>=4.0.0
unstructured>=0.12.0
pgvector>=0.2.4

# API & Web
fastapi==0.121.2
uvicorn==0.34.0

# Database
psycopg2-binary==2.9.9
sqlalchemy>=2.0.0
redis==5.2.1

# ML & Data
numpy>=1.26.0
pandas>=2.1.0
scikit-learn>=1.4.0
xgboost>=2.0.0

# LLM
openai==2.8.0

# Configuration & Logging
pydantic==2.12.4
pydantic-settings==2.7.1
structlog>=24.1.0
python-dotenv>=1.0.0
```

**Main API Endpoints**:
- `POST /api/v1/generate-lesson` - Generate personalized lesson
- `POST /api/v1/ingest-documents` - Upload & process documents (background)
- `POST /api/v1/validate-safety` - Safety validation
- `GET /api/v1/status` - Service status
- `GET /health` - Health check

### 3.2 Rails API Service (`/app/rails_api`)

**Language**: Ruby 3.2+
**Framework**: Rails 7.2.3 (API mode)
**Port**: 3000 (development), ECS container (production)

**Directory Structure**:
```
app/rails_api/
├── app/
│   ├── controllers/
│   │   ├── application_controller.rb  # Base controller
│   │   ├── health_controller.rb       # Health checks
│   │   └── api/v1/
│   │       ├── learners_controller.rb         # Learner CRUD
│   │       └── learning_paths_controller.rb   # Progress tracking
│   │
│   ├── models/
│   │   ├── learner.rb           # User profile, metrics
│   │   ├── learning_path.rb     # Learning journey
│   │   ├── lesson.rb            # Content delivery
│   │   └── quiz_response.rb     # Assessment results
│   │
│   ├── services/
│   │   ├── ai_service_client.rb     # HTTParty client to AI service
│   │   └── lesson_delivery_service.rb # Multi-channel delivery
│   │
│   ├── jobs/
│   │   └── lesson_delivery_job.rb   # Sidekiq background job
│   │
│   └── channels/                    # Action Cable (optional)
│
├── config/
│   ├── puma.rb                  # Puma web server config
│   ├── sidekiq.yml              # Sidekiq job queue config
│   ├── database.yml             # PostgreSQL connection
│   └── routes.rb                # API routes
│
├── db/
│   └── migrate/
│       ├── 20250101_create_learners.rb
│       ├── 20250101_create_learning_paths.rb
│       ├── 20250101_create_lessons.rb
│       └── 20250101_create_quiz_responses.rb
│
├── spec/                        # RSpec tests
│   ├── models/
│   ├── controllers/
│   └── services/
│
├── Gemfile                      # Ruby dependencies
├── Dockerfile                   # Container image
└── Gemfile.lock                 # Dependency lock file
```

**Key Dependencies**:
```ruby
# Framework
rails ~> 7.2.3
puma ~> 6.4

# Database
pg ~> 1.5
redis ~> 5.3

# Background Jobs
sidekiq ~> 7.3

# API & Serialization
blueprinter ~> 1.0
rack-cors ~> 2.0
jbuilder ~> 2.11

# Authentication & Security
devise ~> 4.9
devise-jwt ~> 0.11
pundit ~> 2.3

# External Services
httparty ~> 0.21
twilio-ruby ~> 6.9
slack-ruby-client ~> 2.2

# Functional Programming
dry-monads ~> 1.6
dry-validation ~> 1.10

# Security Scanning
brakeman ~> 6.1

# Testing (dev/test)
rspec-rails ~> 6.1
factory_bot_rails ~> 6.4
webmock ~> 3.20
vcr ~> 6.2
```

**Main Database Models**:
- **Learner**: User profile, completion rates, accuracy metrics
- **LearningPath**: Personalized curriculum, progress tracking
- **Lesson**: Generated content, delivery metadata
- **QuizResponse**: Assessment results, engagement analytics

**Main API Endpoints**:
- `POST /api/v1/learners` - Create learner
- `GET /api/v1/learners/:id` - Get learner profile
- `GET /api/v1/learners/:id/progress` - Get progress
- `POST /api/v1/quiz_responses` - Submit quiz answer
- `GET /api/v1/analytics/dashboard` - Analytics aggregation

### 3.3 ML Pipeline (`/ml_pipeline`)

**Language**: Python (scikit-learn, XGBoost, Optuna)
**Purpose**: Engagement prediction, risk classification, model retraining

**Directory Structure**:
```
ml_pipeline/
├── training/
│   ├── engagement_predictor.py  # XGBoost engagement model
│   ├── risk_classifier.py       # Risk classification
│   └── feature_engineering.py   # Feature extraction
│
├── evaluation/
│   ├── metrics.py               # Model evaluation metrics
│   └── cross_validation.py      # CV strategies
│
├── models/
│   ├── engagement_predictor.pkl # Trained model artifact
│   ├── risk_classifier.pkl
│   └── feature_scaler.pkl
│
└── deployment/
    └── inference.py             # Batch inference script
```

**Key Components**:
- **Engagement Predictor**: XGBoost predicts optimal lesson delivery times
- **Risk Classifier**: Identifies struggling learners needing intervention
- **Feature Store**: Redis-backed real-time features (learner behavior)

---

## 4. DATABASE & INFRASTRUCTURE DEPENDENCIES

### 4.1 Primary Database: PostgreSQL 16

**Role**: Transactional data, relational schema, vector storage (pgvector)

**Connection String**: `postgresql://user:pass@host:5432/bmo_learning_prod`

**Key Tables**:
```sql
learners                  -- User profiles, completion metrics
learning_paths           -- Personalized curricula, progress
lessons                  -- Generated lesson content
quiz_responses           -- Assessment results, engagement
```

**pgvector Extension**:
- Enables vector similarity search in PostgreSQL
- Alternative to Chroma for production deployments
- Reduces operational complexity

### 4.2 Vector Store: Chroma 0.5.23

**Role**: Document embeddings, semantic search (RAG)

**Collections**:
- `bmo_training_docs` - Financial training materials
- Metadata filtering (topic, compliance status, version)

**Migration Path**: Production can migrate to PostgreSQL pgvector extension

### 4.3 Cache & Job Queue: Redis 7-alpine

**Role**:
- LLM response caching (60%+ cache hit rate)
- Sidekiq job queue
- Session storage
- Feature store (ML real-time features)

**Connection String**: `redis://host:6379/0`

**Use Cases**:
- Cache OpenAI responses (cost optimization)
- Queue lesson delivery jobs
- Store learner session state
- ML feature computation

### 4.4 Object Storage: AWS S3 (Production)

**Role**: Training documents, model artifacts, backups

**Buckets**:
- `bmo-learning-training-docs` - Source documents for ingestion
- `bmo-learning-model-artifacts` - ML models, scalers
- `bmo-learning-terraform-state` - Terraform state backups

---

## 5. DOCKER & CONTAINERIZATION

### 5.1 Docker Compose (Local Development)

**File**: `docker-compose.yml`

**Services**:
1. **postgres** (ankane/pgvector:latest)
   - Port: 5432
   - Database: bmo_learning_dev
   - Volume: postgres_data:/var/lib/postgresql/data

2. **redis** (redis:7-alpine)
   - Port: 6379
   - Volume: redis_data:/data

3. **ai_service** (custom Python image)
   - Port: 8000
   - Build: `./app/ai_service/Dockerfile`
   - Command: `uv run uvicorn app.main:app --reload`
   - Dependencies: postgres, redis (healthcheck)

4. **rails_api** (custom Ruby image)
   - Port: 3000
   - Build: `./app/rails_api/Dockerfile`
   - Command: `bundle exec puma`
   - Dependencies: postgres, redis

5. **sidekiq** (same Ruby image as rails_api)
   - No external port
   - Command: `bundle exec sidekiq`
   - Dependencies: postgres, redis

**Volume Management**:
- `postgres_data` - Database persistence
- `redis_data` - Cache persistence
- `ai_service_cache` - Python package cache
- `rails_bundle` - Ruby gem cache (shared)

### 5.2 Container Images

#### Python AI Service Dockerfile
```dockerfile
FROM python:3.11-slim
RUN useradd -m -u 1000 appuser
WORKDIR /app
RUN apt-get update && apt-get install -y gcc g++
RUN pip install uv
COPY pyproject.toml ./
RUN uv sync --frozen
COPY . .
USER appuser
EXPOSE 8000
HEALTHCHECK CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Key Points**:
- Non-root user (appuser, UID 1000) for security
- Layer caching: dependencies before code
- Health check validates service availability
- `uv` package manager for fast dependency installation

#### Rails API Dockerfile
```dockerfile
FROM ruby:3.2.2-slim
RUN useradd -m -u 1000 appuser
WORKDIR /app
RUN apt-get update && apt-get install -y build-essential libpq-dev nodejs curl
COPY Gemfile Gemfile.lock ./
RUN bundle install
COPY . .
RUN chown -R appuser:appuser /app
USER appuser
EXPOSE 3000
HEALTHCHECK CMD curl -f http://localhost:3000/health || exit 1
CMD ["bundle", "exec", "puma", "-C", "config/puma.rb"]
```

**Key Points**:
- Non-root execution
- NodeJS included for optional asset pipeline
- PostgreSQL development libraries for `pg` gem
- Health check via curl

### 5.3 Test Docker Compose

**File**: `docker-compose.test.yml`

Used for CI/CD and integration testing. Minimal configuration focusing on core services.

---

## 6. BUILD & DEPLOYMENT SCRIPTS

### 6.1 Development Setup

**File**: `scripts/dev-setup.sh`

**Purpose**: Bootstrap development environment

**Steps**:
1. Verify prerequisites (Docker, Python 3.11+, Ruby 3.2+)
2. Copy `.env.example` to `.env`
3. Install Python dependencies: `uv sync --all-extras`
4. Install Ruby dependencies: `bundle install`
5. Setup pre-commit hooks
6. Start databases: `docker-compose up -d postgres redis`
7. Create and migrate database: `rails db:create db:migrate`
8. Seed test data (optional)

**Usage**:
```bash
chmod +x scripts/dev-setup.sh
./scripts/dev-setup.sh
docker-compose up  # Start all services
```

### 6.2 CI/CD Pipeline (GitHub Actions)

#### Python Tests (`.github/workflows/python-tests.yml`)

**Trigger**: Push/PR to main/develop, changes in `app/ai_service/**`

**Jobs**:
1. **Setup** (ubuntu-latest)
   - Python 3.11
   - PostgreSQL service (pgvector)
   - uv package manager

2. **Steps**:
   - Checkout code
   - Install dependencies: `uv sync --all-extras`
   - Lint: `uv run ruff check .`
   - Type check: `uv run mypy .`
   - Tests: `uv run pytest --cov`
   - Coverage upload

#### Rails Tests (`.github/workflows/rails-tests.yml`)

**Trigger**: Push/PR to main/develop, changes in `app/rails_api/**`

**Services**:
- PostgreSQL 16
- Redis 7-alpine

**Steps**:
- Ruby 3.2.2 with bundler caching
- Bundle install
- RuboCop linting
- RSpec tests with coverage
- Coverage upload

#### Security Scanning (`.github/workflows/security.yml`)

**Checks**:
- SAST: Brakeman (Ruby), Bandit (Python)
- Dependency scanning: detect-secrets
- SCA: Vulnerable dependencies

---

## 7. EXTERNAL SERVICE INTEGRATIONS

### 7.1 OpenAI API

**Environment Variables**:
```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview
```

**Usage**:
- **Embeddings**: text-embedding-3-small (RAG retrieval)
- **Content Generation**: GPT-4 (lesson creation)
- **Moderation**: OpenAI Moderation API (content safety)

**Integration Points**:
- Python AI service: LangChain OpenAI integration
- Safety validator: Constitutional AI checks

### 7.2 Slack Integration

**Environment Variables**:
```
SLACK_BOT_TOKEN=xoxb-...
```

**Features**:
- Direct message delivery of lessons
- Quiz response collection
- Progress notifications

**Implementation**: `app/rails_api/app/services/lesson_delivery_service.rb`

### 7.3 Twilio SMS

**Environment Variables**:
```
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
```

**Features**:
- SMS lesson delivery
- Quiz response submission via SMS
- Engagement notifications

**Implementation**: Twilio Ruby client integration

### 7.4 AWS Services (Production)

**Services**:
- **S3**: Document storage, backups
- **ECR**: Docker image registry
- **ECS/Fargate**: Container orchestration
- **RDS**: Managed PostgreSQL
- **ElastiCache**: Managed Redis
- **Secrets Manager**: Credential management
- **CloudWatch**: Logging, monitoring
- **ALB**: Application Load Balancer
- **CloudFront**: CDN (future)

---

## 8. TERRAFORM INFRASTRUCTURE

### 8.1 Configuration Structure

```
infrastructure/terraform/
├── environments/
│   ├── dev/
│   │   └── main.tf
│   ├── staging/
│   │   └── main.tf
│   └── prod/
│       ├── main.tf              # Environment orchestration
│       ├── terraform.tfvars.example
│       └── .terraform/           # State management
│
└── modules/
    ├── vpc/
    │   └── main.tf              # VPC, subnets, security groups
    └── ecs/
        └── main.tf              # ECS cluster, task definitions
```

### 8.2 VPC Module (`infrastructure/terraform/modules/vpc/main.tf`)

**Resources**:
- **VPC**: CIDR 10.0.0.0/16 (customizable)
- **Public Subnets**: Internet-facing (ALB, NAT)
- **Private Subnets**: No internet access (databases, workers)
- **Internet Gateway**: Route to public internet
- **NAT Gateway**: Outbound access from private subnets (production)
- **Route Tables**: Public/private routing

**Variables**:
- `vpc_cidr`: VPC CIDR block
- `environment`: dev/staging/prod
- `availability_zones`: Multi-AZ deployment (default: 2)

### 8.3 ECS Module (`infrastructure/terraform/modules/ecs/main.tf`)

**Resources**:
- **ECS Cluster**: Container orchestration
  - Container Insights enabled (monitoring)
  - Capacity Providers: FARGATE + FARGATE_SPOT
  
- **CloudWatch Log Group**: `/ecs/{cluster_name}`
  - Retention: 30 days

**Capacity Strategy**:
- Base: 1 FARGATE task (always running)
- Weight: 100 (prefer FARGATE over SPOT)
- SPOT: For cost optimization in non-critical

### 8.4 Production Environment (`infrastructure/terraform/environments/prod/main.tf`)

**Terraform Config**:
- Backend: S3 (`bmo-learning-terraform-state`)
- Region: us-east-2
- State locking: DynamoDB (`terraform-state-lock`)

**Modules Provisioned**:
1. **VPC Module**
   - CIDR: 10.0.0.0/16
   - AZs: us-east-2a, us-east-2b, us-east-2c
   
2. **ECS Module**
   - Cluster: `bmo-learning-prod`
   - Environment: production

**Outputs**:
- VPC ID
- ECS cluster name
- Private subnet IDs (for RDS/ElastiCache)

### 8.5 Deployment to AWS us-east-2

**Prerequisites**:
1. AWS account with us-east-2 access
2. Terraform >= 1.5
3. AWS credentials configured
4. S3 bucket for state: `bmo-learning-terraform-state`
5. DynamoDB table for locks: `terraform-state-lock`

**Deployment Steps**:
```bash
cd infrastructure/terraform/environments/prod

# Initialize (first time)
terraform init

# Plan changes
terraform plan -out=tfplan

# Apply infrastructure
terraform apply tfplan

# Outputs will show VPC ID, ECS cluster name, etc.
```

**Estimated Cost (900 learners)**:
- ECS Fargate: $300/month
- RDS PostgreSQL: $200/month
- ElastiCache Redis: $100/month
- Misc (S3, ALB, CloudWatch): $200/month
- **Infrastructure Total**: $800-1,200/month

**Additional Costs**:
- OpenAI LLM: $300-500/month (GPT-4)
- OpenAI Embeddings: $100/month
- Moderation API: $50/month
- **LLM Total**: $450-650/month

**Grand Total**: ~$1,250-1,850/month (production)

---

## 9. CONFIGURATION & ENVIRONMENT SETUP

### 9.1 Environment Variables

**File**: `.env.example`

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
AWS_REGION=us-east-2

# External Services
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
SLACK_BOT_TOKEN=

# Application
RAILS_ENV=development
PYTHON_ENV=development
LOG_LEVEL=INFO
```

### 9.2 Python Settings (`app/ai_service/config/settings.py`)

Pydantic v2 settings management:
- Environment variable loading
- Type validation
- Default values
- API key management

### 9.3 Rails Configuration

**Database** (`config/database.yml`):
- Postgres connection pooling
- Replica endpoints (staging/prod)

**Sidekiq** (`config/sidekiq.yml`):
- Concurrency: 5 (development), 20+ (production)
- Queues: critical, default, low
- Retry strategy: exponential backoff

**Puma** (`config/puma.rb`):
- Workers: auto-scaled by CPU count
- Threads: 5-16 per worker
- Port: 3000

---

## 10. TESTING STRATEGY

### 10.1 Python Testing (AI Service)

**Framework**: pytest with coverage

**Test Structure**:
```
app/ai_service/tests/
├── unit/
│   ├── test_safety_validator.py
│   ├── test_lesson_generator.py
│   └── test_retrievers.py
│
├── integration/
│   ├── test_ai_service_client.py
│   └── test_vector_store.py
│
└── conftest.py              # Fixtures
```

**Coverage Requirement**: >80%
**Command**: `uv run pytest --cov`

### 10.2 Rails Testing (API Service)

**Framework**: RSpec with Rails

**Test Structure**:
```
app/rails_api/spec/
├── models/
│   ├── learner_spec.rb
│   ├── learning_path_spec.rb
│   └── quiz_response_spec.rb
│
├── controllers/
│   └── api/v1/
│       ├── learners_controller_spec.rb
│       └── learning_paths_controller_spec.rb
│
└── services/
    ├── ai_service_client_spec.rb
    └── lesson_delivery_service_spec.rb
```

**Tools**:
- Factory Bot: Test data generation
- WebMock: HTTP mocking
- VCR: HTTP cassettes for replay

**Coverage Requirement**: >80%
**Command**: `bundle exec rspec`

---

## 11. SECURITY ARCHITECTURE

### 11.1 Defense-in-Depth Layers

**Layer 1: Network**
- VPC with private subnets (databases not exposed)
- Security groups (least privilege)
- WAF (SQL injection, XSS)

**Layer 2: Application**
- JWT authentication (Rails)
- API rate limiting (60 req/min)
- Input validation (Pydantic, dry-validation)
- CORS restrictions

**Layer 3: AI Safety**
- Prompt injection detection
- Constitutional AI (output validation)
- PII detection & redaction
- Content moderation
- Output token limits

**Layer 4: Data**
- Encryption at rest (RDS, S3)
- Encryption in transit (TLS 1.3)
- AWS Secrets Manager (credentials)
- PII anonymization in logs

**Layer 5: Monitoring**
- Audit logging (all API calls)
- Anomaly detection (GuardDuty)
- Security scanning (CI/CD)
- Incident response plan

### 11.2 Key Security Components

**PII Detection** (`app/ai_service/safety/safety_validator.py`):
- Email, phone, SSN, credit card detection
- Automatic redaction
- Compliance-aware

**Constitutional AI**:
- Safety principles for financial services
- Multi-check validation
- Fallback responses

**Content Moderation**:
- OpenAI Moderation API
- Unsafe content filtering
- Compliance validation

---

## 12. IMPLEMENTATION STATUS

### Phases Completed:

- **Phase 1**: Foundation & Setup ✅
- **Phase 2**: LangChain AI Service ✅
- **Phase 3**: Rails API Service ✅
- **Phase 4**: ML Pipeline & Analytics ✅
- **Phase 5**: Infrastructure & Deployment ✅
- **Phase 6**: Security & Compliance ✅

**Files Delivered**: 100+
**Code Size**: 200+ KB (production-ready)
**Documentation**: Comprehensive (15+ docs)

---

## 13. LANGCHAIN PATTERNS DEMONSTRATED

| Pattern | Use Case | File |
|---------|----------|------|
| **RAG Pipeline** | Semantic document retrieval | `ingestion/vector_store.py` |
| **MultiQuery Retriever** | Query expansion | `retrievers/multi_query_retriever.py` |
| **Parent Document Retriever** | Context preservation | Same file |
| **LCEL Chains** | Multi-stage generation | `generators/lesson_generator.py` |
| **Prompt-based Safety** | Output validation | `safety/safety_validator.py` |
| **Tool-Calling Agent** | Structured execution | `agents/learning_orchestrator.py` |
| **Conversation Memory** | Context across sessions | Same file |
| **Few-Shot Prompts** | Consistent formatting | `generators/few_shot_prompts.py` |
| **Output Parsers** | Pydantic v2 validation | `parsers/output_parser.py` |
| **JsonOutputParser** | Structured JSON | Same file |
| **LLM Caching** | Cost optimization | `utils/caching.py` |
| **Callback Handlers** | Monitoring & observability | `callbacks/monitoring.py` |

---

## 14. QUICK START GUIDE

### Local Development (Docker Compose)

```bash
# 1. Clone repository
git clone <repo-url>
cd learning-app

# 2. Setup environment
./scripts/dev-setup.sh

# 3. Start services
docker-compose up

# 4. Verify health
curl http://localhost:3000/health
curl http://localhost:8000/health

# 5. Access APIs
# Rails API: http://localhost:3000
# Python FastAPI: http://localhost:8000/docs
```

### AWS Deployment (Terraform)

```bash
# 1. Configure AWS credentials
export AWS_REGION=us-east-2

# 2. Deploy infrastructure
cd infrastructure/terraform/environments/prod
terraform init
terraform plan
terraform apply

# 3. Deploy services (push to ECR, deploy via ECS)
# (Manual or via CI/CD pipeline)

# 4. Verify deployment
aws ecs describe-services --cluster bmo-learning-prod \
  --services ai-service rails-api --region us-east-2
```

---

## 15. KEY METRICS & PERFORMANCE TARGETS

### Availability
- SLA: 99.9% uptime (production)
- RTO: <2 hours
- RPO: <24 hours

### Performance
- API response time: <500ms (p95)
- AI service latency: <2s (lesson generation)
- Database query latency: <100ms (p95)

### Cost Optimization
- LLM cache hit rate: 60%+
- Redis saves: 5x on API calls
- Reserved instances: 40% savings
- Spot instances (dev/staging): 70% savings

### Learning Outcomes
- Completion rate: 70% (target)
- Quiz accuracy: 85%+ (target)
- Time to competency: <4 weeks (target)

---

## 16. DEPLOYMENT CHECKLIST FOR AWS us-east-2

- [ ] AWS account configured (us-east-2)
- [ ] Terraform backend S3 bucket created
- [ ] DynamoDB state lock table created
- [ ] ECR repositories created (ai-service, rails-api)
- [ ] RDS PostgreSQL instance deployed
- [ ] ElastiCache Redis cluster deployed
- [ ] ECS cluster provisioned (via Terraform)
- [ ] Task definitions updated with image URLs
- [ ] ALB configured with target groups
- [ ] Route 53 DNS configured
- [ ] Secrets Manager credentials loaded
- [ ] CloudWatch dashboards created
- [ ] Auto-scaling policies configured
- [ ] Backup snapshots scheduled
- [ ] Load test completed
- [ ] Security scanning passed
- [ ] Disaster recovery tested

---

## 17. SUPPORT & DOCUMENTATION

**Key Documentation Files**:
- `README.md` - Project overview
- `docs/architecture/overview.md` - System design
- `docs/workplans/00-MASTER-WORKPLAN.md` - Implementation phases
- `IMPLEMENTATION-COMPLETE.md` - Detailed completion status

**Additional Resources**:
- LangChain: https://python.langchain.com/
- FastAPI: https://fastapi.tiangolo.com/
- Rails: https://guides.rubyonrails.org/
- Terraform: https://www.terraform.io/docs

---

**Generated**: 2025-11-16
**Status**: Ready for AWS us-east-2 Deployment
