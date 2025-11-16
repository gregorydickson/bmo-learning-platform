# BMO Learning Platform - Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         External Interfaces                          │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐     │
│  │  Slack   │    │   SMS    │    │  Email   │    │  Admin   │     │
│  │  Bot     │    │ (Twilio) │    │          │    │   UI     │     │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘     │
└───────┼──────────────┼──────────────┼──────────────┼───────────────┘
        │              │              │              │
        └──────────────┴──────────────┴──────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Application Layer (Rails)                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    Rails API Service (Port 3000)                │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │ │
│  │  │  Controllers │  │   Services   │  │    Models    │         │ │
│  │  │  - Learners  │  │  - Learning  │  │  - Learner   │         │ │
│  │  │  - Lessons   │  │    Orchestr. │  │  - Lesson    │         │ │
│  │  │  - Analytics │  │  - Delivery  │  │  - Progress  │         │ │
│  │  └───────┬──────┘  └──────┬───────┘  └──────┬───────┘         │ │
│  └──────────┼────────────────┼──────────────────┼─────────────────┘ │
└─────────────┼────────────────┼──────────────────┼───────────────────┘
              │                │                  │
              ▼                ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Background Jobs (Sidekiq)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │   Scheduler  │  │   Delivery   │  │  Analytics   │             │
│  │     Jobs     │  │     Jobs     │  │     Jobs     │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
              │                │                  │
              └────────────────┼──────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    AI Service Layer (Python)                         │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │              Python AI Service (FastAPI - Port 8000)           │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │ │
│  │  │   Document   │  │  LangChain   │  │    Safety    │         │ │
│  │  │  Ingestion   │  │   Agents     │  │    Layer     │         │ │
│  │  │  - Loaders   │  │  - Learning  │  │  - Const. AI │         │ │
│  │  │  - Chunking  │  │    Orchestr. │  │  - PII Det.  │         │ │
│  │  │  - Embedding │  │  - Content   │  │  - Moder.    │         │ │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │ │
│  └─────────┼──────────────────┼──────────────────┼─────────────────┘ │
└────────────┼──────────────────┼──────────────────┼───────────────────┘
             │                  │                  │
             ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Data & ML Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │  Vector DB   │  │  PostgreSQL  │  │     Redis    │             │
│  │  (Chroma)    │  │  (pgvector)  │  │  - Cache     │             │
│  │  - Embeddings│  │  - Business  │  │  - Sidekiq   │             │
│  │  - RAG       │  │    Data      │  │  - Sessions  │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │  ML Pipeline │  │  OpenAI API  │  │      S3      │             │
│  │  - XGBoost   │  │  - GPT-4     │  │  - Training  │             │
│  │  - Predictor │  │  - Embeddings│  │    Docs      │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### Rails API Service
**Technology**: Ruby on Rails 7.1 (API mode)
**Port**: 3000
**Responsibilities**:
- Business logic and workflow orchestration
- Learner management (profiles, progress tracking)
- Learning path personalization
- Delivery channel coordination (Slack, SMS, Email)
- Analytics aggregation
- Authentication & authorization

**Key Patterns**:
- Service Objects (functional programming with dry-monads)
- Repository Pattern (data access abstraction)
- Circuit Breaker (AI service integration)
- CQRS (read/write separation for analytics)

### Python AI Service
**Technology**: Python 3.11+ with LangChain, FastAPI
**Port**: 8000
**Responsibilities**:
- Document ingestion & RAG pipeline
- Content generation (lessons, scenarios, quizzes)
- Adaptive learning agent
- LLM safety (Constitutional AI, PII detection, moderation)
- Response caching

**Key Patterns**:
- Sequential Chains (multi-stage content generation)
- Agents with Tools (adaptive learning orchestration)
- Constitutional AI (safety guardrails)
- Parent Document Retriever (context preservation)
- Output Fixing Parser (robust LLM responses)

### ML Pipeline
**Technology**: Python (XGBoost, scikit-learn, Optuna)
**Responsibilities**:
- Engagement prediction (when to send lessons)
- Risk classification (identify struggling learners)
- Feature engineering (behavioral, temporal, content)
- A/B testing framework
- Model retraining

**Key Patterns**:
- Feature Store (Redis for real-time features)
- Model Registry (MLflow for versioning)
- Batch + Real-time Inference

### Background Jobs (Sidekiq)
**Technology**: Ruby with Sidekiq (Redis-backed)
**Responsibilities**:
- Daily lesson scheduling
- Multi-channel delivery
- Engagement analytics computation
- Model retraining triggers

**Key Patterns**:
- Job Priority Queues (critical, default, low)
- Retry with Exponential Backoff
- Dead Letter Queue (failed job handling)

### Data Layer

#### PostgreSQL (with pgvector)
**Responsibilities**:
- Primary data store (learners, lessons, progress, analytics)
- Vector similarity search (alternative to Chroma)
- Transactional consistency

**Schema Highlights**:
- `learners` - User profiles and preferences
- `learning_paths` - Personalized curricula
- `microlessons` - Generated content
- `assessment_results` - Quiz performance
- `engagement_metrics` - Tracking data

#### Vector Store (Chroma)
**Responsibilities**:
- Document embeddings storage
- Semantic similarity search
- RAG retrieval

**Collections**:
- `bmo_training_docs` - Training materials
- Metadata filtering (topic, compliance status, version)

#### Redis
**Responsibilities**:
- LLM response caching (reduce API costs)
- Sidekiq job queue
- Session storage
- Feature store (ML real-time features)

## Data Flow Examples

### Lesson Generation Flow
```
1. Learner requests lesson (via Slack)
   ↓
2. Rails receives request, calls AI service
   ↓
3. Python AI service:
   a. Retrieves learner state (knowledge gaps)
   b. Queries vector store for relevant content (RAG)
   c. Generates lesson with Sequential Chain
   d. Applies Constitutional AI safety checks
   e. Validates output schema (Pydantic)
   f. Content moderation (OpenAI API)
   ↓
4. Rails receives lesson, stores in database
   ↓
5. Background job delivers via Slack API
   ↓
6. Learner receives lesson in Slack DM
```

### Adaptive Scheduling Flow
```
1. Daily scheduler job runs (Sidekiq cron)
   ↓
2. Queries learners due for lessons
   ↓
3. For each learner:
   a. Fetch historical engagement data
   b. Call ML predictor API (best delivery time)
   c. Get risk score (struggling learner?)
   d. Request lesson from AI service
   e. Schedule delivery job at predicted optimal time
   ↓
4. Delivery job executes at scheduled time
   ↓
5. Tracks engagement (open, response time, quiz score)
   ↓
6. Feeds data back to ML pipeline for retraining
```

### RAG Pipeline Flow
```
1. Document ingestion (one-time or periodic):
   a. Load PDFs from S3
   b. Split into chunks (500 tokens, 50 overlap)
   c. Generate embeddings (OpenAI text-embedding-3-small)
   d. Store in Chroma with metadata
   ↓
2. Query-time retrieval:
   a. User query → embedding
   b. Semantic search (top-k similar chunks)
   c. Parent Document Retriever (fetch full context)
   d. Contextual compression (reduce irrelevant portions)
   e. Pass to LLM as context
```

## Security Architecture

### Defense in Depth

**Layer 1: Network Security**
- VPC with private subnets (databases not internet-accessible)
- Security groups (least privilege)
- WAF (SQL injection, XSS protection)

**Layer 2: Application Security**
- JWT authentication (Rails API)
- API rate limiting (60 req/min per user)
- Input validation (Pydantic, dry-validation)
- CORS restrictions

**Layer 3: AI Security**
- Prompt injection detection
- Constitutional AI (output validation)
- PII detection & redaction
- Content moderation
- Output token limits (prevent runaway generation)

**Layer 4: Data Security**
- Encryption at rest (RDS, S3)
- Encryption in transit (TLS 1.3)
- Secrets management (AWS Secrets Manager)
- PII anonymization in logs

**Layer 5: Monitoring**
- Audit logging (all API calls)
- Anomaly detection (GuardDuty)
- Security scanning (SAST, DAST, SCA)
- Incident response plan

## Scalability Considerations

### Horizontal Scaling
- **Rails API**: Auto-scaling ECS tasks (target CPU 70%)
- **Python AI**: Auto-scaling ECS tasks (target request latency <2s)
- **Sidekiq**: Multi-worker instances (scale with queue depth)
- **Databases**: RDS read replicas (analytics queries)

### Performance Optimization
- **LLM Caching**: 60%+ cache hit rate (reduces costs 5x)
- **Connection Pooling**: pgBouncer for PostgreSQL
- **Async Processing**: Background jobs for slow operations
- **CDN**: CloudFront for static assets (future)

### Cost Optimization
- **Spot Instances**: Development/staging environments (70% savings)
- **Reserved Instances**: Production databases (40% savings)
- **LLM Cache**: Redis cache prevents duplicate OpenAI calls
- **Batch Processing**: Nightly aggregations vs real-time

## Technology Decisions (ADRs)

### ADR-001: LangChain for AI Orchestration
**Decision**: Use LangChain as primary AI framework
**Rationale**: Rich tooling for RAG, agents, chains, memory. Constitutional AI for safety.
**Trade-offs**: Abstraction complexity, version churn

### ADR-002: Rails + Python Microservices
**Decision**: Separate Rails (business logic) and Python (AI)
**Rationale**: Best tool for each job. Independent scaling. Clear boundaries.
**Trade-offs**: Network latency, operational complexity

### ADR-003: PostgreSQL + pgvector vs Dedicated Vector DB
**Decision**: Use Chroma for development, migrate to pgvector for production
**Rationale**: Single database simplifies operations. pgvector sufficient for <1M vectors.
**Trade-offs**: Chroma has richer features (but adds complexity)

### ADR-004: Constitutional AI for Safety
**Decision**: Mandatory Constitutional AI on all generated content
**Rationale**: Financial services require accuracy and compliance.
**Trade-offs**: Increased latency (~2x LLM calls), higher costs

### ADR-005: XGBoost over Deep Learning
**Decision**: Use XGBoost for engagement prediction
**Rationale**: Tabular data, small dataset (900 learners), interpretability
**Trade-offs**: May underperform DL at scale (10K+ learners)

## Deployment Environments

### Development (Local)
- Docker Compose
- Mock external services (Twilio, Slack)
- Local Chroma vector store
- Reduced LLM caching

### Staging (AWS)
- Mirrors production architecture (smaller instances)
- Synthetic data (900 test learners)
- Full integration testing
- Cost: ~$200/month

### Production (AWS)
- Multi-AZ for high availability
- Auto-scaling (2-10 instances)
- Managed services (RDS, ElastiCache)
- Cost: ~$800-1,200/month (900 learners)

## Monitoring & Observability

### Metrics
- **Application**: Request latency, error rates, throughput
- **AI**: LLM token usage, cache hit rate, safety violations
- **ML**: Model accuracy, prediction latency, drift detection
- **Business**: Completion rate, engagement score, quiz performance

### Logging
- **Structured Logs**: JSON format (parsable)
- **Log Aggregation**: CloudWatch Logs Insights
- **Retention**: 30 days (compliance)

### Alerting
- **Critical**: Service down, database unreachable
- **High**: Error rate >5%, latency >5s
- **Medium**: LLM safety violations, model drift
- **Low**: Cache hit rate <50%, disk usage >80%

## Disaster Recovery

### Backup Strategy
- **Database**: Automated daily snapshots (7-day retention)
- **Vector Store**: Weekly S3 backups
- **Application**: Immutable Docker images (ECR)

### Recovery Objectives
- **RTO (Recovery Time)**: <2 hours
- **RPO (Recovery Point)**: <24 hours (daily backups)

### Failover Plan
1. Detect failure (automated alerts)
2. Promote read replica to primary (RDS)
3. Restore vector store from S3
4. Redeploy services to backup region (future)

---

**Last Updated**: 2025-11-15
**Version**: 1.0
**Reviewers**: Architecture review pending
