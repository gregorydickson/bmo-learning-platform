# BMO Learning Platform - Documentation Index

**Last Updated**: 2025-11-16
**Status**: Production-Ready for AWS us-east-2 Deployment

---

## Start Here

### Quick Overview (5 minutes)
1. **[DEPLOYMENT-SUMMARY.md](DEPLOYMENT-SUMMARY.md)** (369 lines)
   - Quick facts and key metrics
   - Architecture overview
   - Cost breakdown
   - Deployment checklist

### Comprehensive Architecture (30 minutes)
2. **[CODEBASE-OVERVIEW.md](CODEBASE-OVERVIEW.md)** (1,085 lines)
   - Complete codebase walkthrough
   - All components and services explained
   - Database schema and dependencies
   - Docker and Terraform configurations
   - Security architecture
   - LangChain patterns demonstrated

### Step-by-Step Deployment (AWS us-east-2)
3. **[AWS-DEPLOYMENT-GUIDE.md](AWS-DEPLOYMENT-GUIDE.md)** (225 lines)
   - Prerequisites and AWS setup
   - Phase-by-phase deployment
   - Infrastructure, databases, services
   - Cost estimation
   - Troubleshooting

---

## Documentation Structure

### By Role

#### For Architects
- [CODEBASE-OVERVIEW.md](CODEBASE-OVERVIEW.md) - Complete system design
- [docs/architecture/overview.md](docs/architecture/overview.md) - Detailed architecture patterns
- [IMPLEMENTATION-COMPLETE.md](IMPLEMENTATION-COMPLETE.md) - What was built

#### For DevOps/Platform Engineers
- [AWS-DEPLOYMENT-GUIDE.md](AWS-DEPLOYMENT-GUIDE.md) - Production deployment
- [DEPLOYMENT-SUMMARY.md](DEPLOYMENT-SUMMARY.md) - Infrastructure overview
- [infrastructure/terraform/](infrastructure/terraform/) - IaC code

#### For Backend Engineers
- [app/ai_service/README.md](app/ai_service/README.md) - Python AI service
- [app/rails_api/README.md](app/rails_api/README.md) - Rails API service
- [CODEBASE-OVERVIEW.md](CODEBASE-OVERVIEW.md) Section 3 - Services & components

#### For Security/Compliance Teams
- [docs/security/SECURITY.md](docs/security/SECURITY.md) - Security policies
- [CODEBASE-OVERVIEW.md](CODEBASE-OVERVIEW.md) Section 11 - Security architecture
- [docs/security/incident-response.md](docs/security/incident-response.md) - Incident response

---

## Project Files Overview

### Root Level Documentation
```
├── README.md                        -- Project overview and features
├── CODEBASE-OVERVIEW.md            -- Complete architecture guide (1,085 lines)
├── DEPLOYMENT-SUMMARY.md           -- Quick deployment reference (369 lines)
├── AWS-DEPLOYMENT-GUIDE.md         -- Step-by-step AWS deployment (225 lines)
├── DOCUMENTATION-INDEX.md          -- This file
├── IMPLEMENTATION-COMPLETE.md      -- Phases 2-6 completion status
├── PHASE1-STATUS.md                -- Phase 1 details
├── .env.example                    -- Environment variables template
└── docker-compose.yml              -- Local development orchestration
```

### Application Code
```
app/
├── ai_service/                     -- Python LangChain AI service (8,000 lines)
│   ├── app/main.py                 -- FastAPI application entry point
│   ├── agents/                     -- LangChain agents
│   ├── chains/                     -- LangChain chains
│   ├── generators/                 -- Content generation
│   ├── ingestion/                  -- Document processing & RAG
│   ├── retrievers/                 -- Vector search
│   ├── safety/                     -- LLM safety (Constitutional AI, PII)
│   ├── pyproject.toml              -- Python dependencies
│   ├── Dockerfile                  -- Container image
│   └── README.md                   -- Service documentation
│
└── rails_api/                      -- Ruby on Rails API service (4,000 lines)
    ├── app/models/                 -- Domain models (Learner, Lesson, etc.)
    ├── app/controllers/            -- REST API endpoints
    ├── app/services/               -- Business logic
    ├── app/jobs/                   -- Sidekiq background jobs
    ├── db/migrate/                 -- Database migrations
    ├── config/                     -- Rails configuration
    ├── Gemfile                     -- Ruby dependencies
    ├── Dockerfile                  -- Container image
    └── README.md                   -- Service documentation
```

### Infrastructure
```
infrastructure/
└── terraform/
    ├── environments/
    │   ├── dev/                    -- Development configuration
    │   ├── staging/                -- Staging configuration
    │   └── prod/                   -- Production configuration (us-east-2)
    │       ├── main.tf             -- Environment orchestration
    │       └── terraform.tfvars.example
    │
    └── modules/
        ├── vpc/                    -- VPC, subnets, networking
        └── ecs/                    -- ECS cluster, services
```

### Machine Learning
```
ml_pipeline/
├── training/                       -- Model training scripts
├── evaluation/                     -- Evaluation metrics
├── models/                         -- Trained model artifacts
└── deployment/                     -- ML deployment
```

### Documentation
```
docs/
├── architecture/
│   └── overview.md                 -- Detailed system design
├── api/                            -- API endpoint documentation
├── security/
│   ├── SECURITY.md                 -- Security policies
│   ├── incident-response.md        -- Incident response procedures
│   └── penetration-testing.md      -- Security testing
└── workplans/
    ├── 00-MASTER-WORKPLAN.md       -- Complete implementation timeline
    ├── 01-foundation-setup.md      -- Phase 1: Foundation
    ├── 02-langchain-service.md     -- Phase 2: AI Service
    ├── 03-rails-api.md             -- Phase 3: Rails API
    ├── 04-ml-analytics.md          -- Phase 4: ML Pipeline
    ├── 05-infrastructure.md        -- Phase 5: Terraform & AWS
    └── 06-security-compliance.md   -- Phase 6: Security & Compliance
```

### CI/CD & Scripts
```
.github/workflows/
├── python-tests.yml                -- Python testing & linting
├── rails-tests.yml                 -- Rails testing & coverage
└── security.yml                    -- Security scanning (SAST, SCA)

scripts/
└── dev-setup.sh                    -- Bootstrap development environment
```

---

## Key Technology Versions

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11+ | AI service |
| Ruby | 3.2+ | Rails API |
| LangChain | 1.0.7 | AI orchestration |
| Rails | 7.2.3 | API framework |
| FastAPI | 0.121 | Python web framework |
| PostgreSQL | 16 | Primary database |
| Redis | 7 | Cache & jobs |
| Chroma | 0.5.23 | Vector store |
| OpenAI | 2.8.0 | LLM provider |
| Sidekiq | 7.3 | Background jobs |
| Terraform | 1.9 | Infrastructure as Code |
| Docker | latest | Containerization |

---

## Deployment Paths

### Path 1: Local Development (Docker Compose)
1. Review: [README.md](README.md) "Quick Start" section
2. Execute: `./scripts/dev-setup.sh`
3. Run: `docker-compose up`
4. Access: http://localhost:3000 and http://localhost:8000/docs

### Path 2: AWS Production (Terraform + ECS)
1. Read: [DEPLOYMENT-SUMMARY.md](DEPLOYMENT-SUMMARY.md) (5 min overview)
2. Follow: [AWS-DEPLOYMENT-GUIDE.md](AWS-DEPLOYMENT-GUIDE.md) (step-by-step)
3. Reference: [CODEBASE-OVERVIEW.md](CODEBASE-OVERVIEW.md) Section 8 (infrastructure details)
4. Monitor: CloudWatch dashboards

### Path 3: Understanding the Architecture
1. Start: [DEPLOYMENT-SUMMARY.md](DEPLOYMENT-SUMMARY.md) "Architecture Overview"
2. Deep dive: [CODEBASE-OVERVIEW.md](CODEBASE-OVERVIEW.md) Sections 1-3
3. Components: Sections 3.1-3.3 (services breakdown)
4. Patterns: Section 13 (LangChain patterns)

---

## Quick Reference

### API Documentation
- **Rails API**: http://localhost:3000 (Swagger available via gem)
- **FastAPI**: http://localhost:8000/docs (Swagger UI)
- **FastAPI**: http://localhost:8000/redoc (ReDoc)

### Database Access
```bash
# PostgreSQL
psql -h localhost -U postgres -d bmo_learning_dev

# Redis
redis-cli -h localhost
```

### Service Ports
- Rails API: 3000
- Python AI Service: 8000
- PostgreSQL: 5432
- Redis: 6379

### Important Commands
```bash
# Local development
docker-compose up -d                # Start services
docker-compose logs -f ai_service   # View AI service logs
docker-compose down                 # Stop services

# Testing
cd app/ai_service && uv run pytest  # Python tests
cd app/rails_api && bundle exec rspec # Rails tests

# Deployment
cd infrastructure/terraform/environments/prod
terraform plan
terraform apply
```

---

## Document Contents Summary

### CODEBASE-OVERVIEW.md (1,085 lines)
- Section 1: Application Architecture & Tech Stack
- Section 2: Directory Structure & Purposes
- Section 3: Services & Components (Python AI, Rails API, ML Pipeline)
- Section 4: Database & Infrastructure Dependencies
- Section 5: Docker & Containerization
- Section 6: Build & Deployment Scripts
- Section 7: External Service Integrations
- Section 8: Terraform Infrastructure (3 modules)
- Section 9: Configuration & Environment Setup
- Section 10: Testing Strategy
- Section 11: Security Architecture
- Section 12: Implementation Status
- Section 13: LangChain Patterns
- Section 14: Quick Start Guide
- Section 15: Metrics & Performance Targets
- Section 16: Deployment Checklist
- Section 17: Support & Documentation

### DEPLOYMENT-SUMMARY.md (369 lines)
- Quick facts table
- Architecture overview
- Production stack details
- Key features & security
- Database schema
- API endpoints
- Environment variables
- Deployment timeline
- Cost breakdown
- Performance metrics
- Comprehensive checklists
- Next steps

### AWS-DEPLOYMENT-GUIDE.md (225 lines)
- Pre-deployment checklist
- AWS prerequisites (S3, DynamoDB, ECR, Secrets Manager)
- Phase 1: Terraform infrastructure
- Phase 2: Database & cache setup
- Phase 3: Docker image build & push
- Phase 4: ECS task definitions
- Phase 5: Auto-scaling
- Phase 6: Database migrations
- Phase 7: Monitoring setup
- Phase 8: Testing & validation
- Phase 9: Backups & DR
- Troubleshooting guide
- Cost estimation table

---

## Getting Help

### For Specific Questions

**Architecture**: See CODEBASE-OVERVIEW.md
**Deployment**: See AWS-DEPLOYMENT-GUIDE.md
**Services**: See app/*/README.md
**Security**: See docs/security/SECURITY.md
**Workplans**: See docs/workplans/00-MASTER-WORKPLAN.md

### External Resources

- **LangChain**: https://python.langchain.com/
- **FastAPI**: https://fastapi.tiangolo.com/
- **Rails**: https://guides.rubyonrails.org/
- **Terraform**: https://www.terraform.io/docs
- **AWS**: https://docs.aws.amazon.com/

---

## Implementation Status

All 6 phases complete and production-ready:

- **Phase 1**: Foundation & Setup ✅ (Completed 2025-11-15)
- **Phase 2**: LangChain AI Service ✅
- **Phase 3**: Rails API Service ✅
- **Phase 4**: ML Pipeline & Analytics ✅
- **Phase 5**: Infrastructure & Deployment ✅
- **Phase 6**: Security & Compliance ✅

**Total deliverables**: 100+ files, 200+ KB code, 1,679 lines of documentation

---

## File Locations Summary

| Document | Location | Size | Purpose |
|----------|----------|------|---------|
| This index | `/DOCUMENTATION-INDEX.md` | 2 KB | Navigation guide |
| Architecture | `/CODEBASE-OVERVIEW.md` | 31 KB | Complete reference |
| Deployment | `/DEPLOYMENT-SUMMARY.md` | 9 KB | Quick overview |
| AWS Guide | `/AWS-DEPLOYMENT-GUIDE.md` | 5 KB | Step-by-step |
| Architecture Details | `/docs/architecture/overview.md` | - | System design |
| Security | `/docs/security/SECURITY.md` | - | Policies |
| Workplans | `/docs/workplans/` | - | Implementation phases |

---

**Status**: Production-Ready
**Region**: AWS us-east-2
**Last Updated**: 2025-11-16
**Version**: 1.0.0 (Complete)

Start with [DEPLOYMENT-SUMMARY.md](DEPLOYMENT-SUMMARY.md) for a quick overview, then refer to [CODEBASE-OVERVIEW.md](CODEBASE-OVERVIEW.md) for detailed architecture.
