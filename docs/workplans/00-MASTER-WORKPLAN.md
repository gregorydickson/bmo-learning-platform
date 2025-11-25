# BMO Learning Platform - Master Workplan

## Project Overview
**Goal**: Create a production-ready microlearning platform demonstrating LangChain best practices
**Purpose**:
1. Demonstrate deep LangChain understanding for potential clients
2. Create viable prototype for BMO or similar enterprise clients
3. Serve as reference implementation for LangChain in production

**Key Differentiators**:
- Enterprise-grade security and compliance
- Production-ready infrastructure (IaC)
- LLM safety and content moderation
- Comprehensive testing and monitoring
- Agent-optimized implementation approach

## Success Criteria
- [x] Demonstrates 10+ LangChain patterns (RAG, agents, chains, memory, tools)
- [x] Includes LLM safety guardrails (Constitutional AI, content filtering)
- [x] Fully containerized with Docker Compose for local development
- [x] Infrastructure as Code (Terraform) for AWS deployment
- [x] 80%+ test coverage across services (85% Python, 82% Rails)
- [x] Security scanning integrated into CI/CD
- [x] API documentation (OpenAPI/Swagger)
- [ ] Performance benchmarks documented (pending deployment)

## Phase Overview

### Phase 1: Foundation & Setup ✅ COMPLETE
**Status**: 100% Complete
**Deliverable**: Scaffolded project with configs, Docker setup, and documentation

See: [workplans/archive/01-foundation-setup.md](./archive/01-foundation-setup.md)

- [x] Project structure and dependency management
- [x] Docker Compose environment
- [x] Development tooling (linting, formatting, pre-commit hooks)
- [x] CI/CD pipeline skeleton
- [x] Security baseline configuration

### Phase 2: LangChain AI Service ✅ COMPLETE
**Status**: 100% Complete
**Deliverable**: Python service with RAG, agents, and content generation

See: [workplans/archive/02-langchain-service.md](./archive/02-langchain-service.md)

- [x] Document ingestion and vector store
- [x] RAG implementation with multiple retrieval strategies
- [x] Adaptive learning agent system
- [x] Content generation pipeline
- [x] LLM safety layer (Constitutional AI, content moderation)
- [x] Comprehensive testing (85% coverage)

### Phase 3: Rails API Service ✅ COMPLETE
**Status**: 100% Complete
**Deliverable**: Rails API with business logic and AI integration

See: [workplans/archive/03-rails-api.md](./archive/03-rails-api.md)

- [x] Domain models and database schema
- [x] Functional service layer
- [x] Python service integration
- [x] Multi-channel delivery (Slack, SMS, Email)
- [x] Background job processing
- [x] API endpoints and authentication (82% coverage)

### Phase 4: ML Pipeline & Analytics ✅ COMPLETE
**Status**: 100% Complete
**Deliverable**: Engagement predictor and analytics dashboard

See: [workplans/archive/04-ml-analytics.md](./archive/04-ml-analytics.md)

- [x] XGBoost engagement predictor
- [x] Risk classification model
- [x] Model training pipeline
- [x] Analytics dashboard
- [x] A/B testing framework

### Phase 5: Infrastructure & Deployment 🔄 IN PROGRESS
**Status**: 70% Complete (Code done, deployment blocked)
**Deliverable**: Production-ready AWS infrastructure

See: [workplans/05-infrastructure.md](./05-infrastructure.md)

- [x] Terraform modules for all AWS services
- [x] Multi-environment setup (prod environment ready)
- [ ] Monitoring and observability (CloudWatch alarms pending)
- [x] Cost optimization (demo config: ~$55/month)
- [ ] Disaster recovery planning (pending deployment)

**Blockers**: See Phase 8 for deployment readiness tasks

### Phase 6: Security & Compliance ✅ MOSTLY COMPLETE
**Status**: 90% Complete (Implementation done, audits pending)
**Deliverable**: Security hardening and compliance documentation

See: [workplans/06-security-compliance.md](./06-security-compliance.md)

- [x] LLM prompt injection protection
- [x] PII detection and redaction
- [x] Security scanning (SAST, DAST, SCA)
- [x] Compliance documentation (SOC2, GDPR considerations)
- [ ] Penetration testing (requires deployed infrastructure)

### Phase 8: Deployment Readiness 🚨 CURRENT FOCUS
**Status**: 20% Complete (Planning done, execution blocked)
**Priority**: CRITICAL
**Deliverable**: Live AWS deployment with all services operational

See: [workplans/08-deployment-readiness.md](./08-deployment-readiness.md)

**Immediate Blockers**:
1. 🔴 Docker images not built/pushed to ECR (PRIMARY BLOCKER)
2. 🔴 Terraform changes uncommitted
3. 🔴 terraform.tfvars needs real ECR image URIs
4. 🟡 S3 state backend verification
5. 🟡 API keys for AWS Secrets Manager

**Next Steps**: Follow Phase 8 workplan sequentially (6 phases, 24 tasks total)

## Critical Path

```mermaid
graph LR
    A[Phase 1: Foundation] --> B[Phase 2: LangChain Service]
    B --> C[Phase 3: Rails API]
    C --> D[Phase 4: ML Pipeline]
    D --> E[Phase 5: Infrastructure]
    A --> F[Phase 6: Security]
    B --> F
    C --> F
    D --> F
    E --> F
```

**Dependencies**:
- Phase 2 requires Phase 1 complete (Docker, configs)
- Phase 3 requires Phase 2 core components (AI service running)
- Phase 4 can run parallel to Phase 3 (separate concerns)
- Phase 5 requires Phase 2-4 (deploying working services)
- Phase 6 runs continuously alongside all phases

## Agent Execution Guidelines

### For Coding Agents
This workplan is optimized for agent execution with these principles:

**✅ DO**:
- Start each session by reading the current phase workplan
- Check off items as completed (update markdown)
- Run tests after each significant implementation
- Commit working code incrementally
- Update documentation alongside code
- Flag blocking issues immediately

**❌ DON'T**:
- Skip tests to move faster
- Implement features not in current phase
- Leave TODO comments instead of implementing
- Commit commented-out code
- Defer documentation to end

### Handoff Protocol
When switching between agents or sessions:

1. **Read current state**: Check latest phase workplan
2. **Review last commits**: Understand what was just completed
3. **Check tests**: Ensure green before continuing
4. **Pick next unchecked item**: Follow sequential order unless blocked
5. **Update workplan**: Check off completed items

### Testing Requirements
Every implementation must include:
- [ ] Unit tests (80%+ coverage)
- [ ] Integration tests for APIs
- [ ] End-to-end tests for critical paths
- [ ] Security tests (input validation, auth)
- [ ] Performance benchmarks where applicable

### Documentation Requirements
Every component must have:
- [ ] README with setup instructions
- [ ] API documentation (for services)
- [ ] Architecture decision records (ADRs) for key choices
- [ ] Inline code documentation (docstrings)
- [ ] Example usage

## Risk Management

### Technical Risks
| Risk | Mitigation | Owner |
|------|-----------|-------|
| LangChain version incompatibility | Pin versions, test upgrades in isolation | Phase 2 |
| LLM API costs during development | Use caching aggressively, local models for testing | Phase 2 |
| Vector store performance at scale | Benchmark early, plan for partitioning | Phase 2 |
| Rails/Python integration complexity | Build robust error handling, circuit breakers | Phase 3 |
| AWS cost overruns | Implement cost monitoring, auto-shutdowns | Phase 5 |

### Security Risks
| Risk | Mitigation | Owner |
|------|-----------|-------|
| Prompt injection attacks | Constitutional AI, input sanitization | Phase 6 |
| PII leakage in logs/embeddings | PII detection, log scrubbing | Phase 6 |
| API authentication bypass | OAuth2, rate limiting, audit logs | Phase 3 |
| Dependency vulnerabilities | Automated scanning, regular updates | Phase 1 |
| Data exfiltration via LLM | Output filtering, sensitive data tagging | Phase 6 |

## Definition of Done

### Feature-Level
- [ ] Code implemented and peer-reviewed
- [ ] Tests passing (unit, integration, E2E)
- [ ] Documentation updated
- [ ] Security scan passed
- [ ] Performance benchmark met
- [ ] Deployed to dev environment
- [ ] Checkbox marked in workplan

### Phase-Level
- [ ] All phase checklist items complete
- [ ] Integration tests with other phases passing
- [ ] Security review completed
- [ ] Documentation comprehensive
- [ ] Demo-ready
- [ ] Tagged release created

### Project-Level
- [ ] All phases complete (Phases 1-4,6 done; Phase 5 at 70%; Phase 8 at 20%)
- [ ] End-to-end system test passing (pending deployment)
- [ ] Security audit passed (implementation done, audit pending)
- [ ] Performance benchmarks met (pending deployment)
- [x] Documentation complete (README, architecture, API docs)
- [ ] Deployment runbook created (in Phase 8 workplan)
- [x] Cost analysis documented (see COST-OPTIMIZATION-SUMMARY.md)
- [ ] Client demo prepared (pending deployment)

## Metrics & KPIs

### Development Metrics
- **Velocity**: Features completed per week
- **Quality**: Test coverage %, bug density
- **Technical Debt**: TODO/FIXME count, code quality scores

### System Metrics
- **Performance**: API response times, LLM latency
- **Reliability**: Uptime %, error rates
- **Cost**: AWS spend per learner, LLM API costs

### Learning Metrics
- **Engagement**: Completion rates, response times
- **Effectiveness**: Quiz scores, knowledge retention
- **Satisfaction**: User feedback scores

## Communication Plan

### Status Updates
- **Daily**: Update workplan checkboxes, commit progress
- **Weekly**: Review phase progress, adjust timeline
- **Phase Completion**: Demo to stakeholders, retrospective

### Escalation Path
- **Blocking Issues**: Flag in workplan, document in ADR
- **Scope Changes**: Update affected phase workplans
- **Security Issues**: Immediate halt, document in security log

## Resources

### External Dependencies
- [ ] OpenAI API key (for embeddings, GPT-4)
- [ ] AWS account (for infrastructure)
- [ ] Twilio account (for SMS)
- [ ] Slack workspace (for testing delivery)
- [ ] GitHub account (for CI/CD)

### Development Tools
- [ ] Python 3.11+
- [ ] Ruby 3.2+
- [ ] Docker Desktop
- [ ] Terraform
- [ ] PostgreSQL (with pgvector)
- [ ] Redis

### Learning Resources
- [LangChain Documentation](https://python.langchain.com/)
- [Constitutional AI Paper](https://arxiv.org/abs/2212.08073)
- [RAG Best Practices](https://docs.anthropic.com/claude/docs/rag)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)

## Next Steps

**Current Status**: Development 85% complete, Deployment 20% complete

**Immediate Actions** (for deployment):
1. 🚨 Read [Phase 8: Deployment Readiness](./08-deployment-readiness.md)
2. 🔴 Build Docker images (PRIMARY BLOCKER)
3. 🔴 Push images to ECR
4. 🔴 Update terraform.tfvars with real ECR URIs
5. 🔴 Commit Terraform changes
6. 🟡 Deploy infrastructure via `terraform apply`
7. 🟡 Configure secrets in AWS Secrets Manager
8. ✅ Verify deployment via health checks

**Decision Points**:
- ✅ After Phase 2: LangChain approach validated
- ✅ After Phase 4: Cost projections reviewed (~$55/month demo config)
- ⏸️ After Phase 8: Go/no-go decision for production launch (pending deployment)

**For Developers**:
- Local development: See `CLAUDE.md` and `GETTING-STARTED.md`
- Current blockers: See `docs/PROJECT-STATUS.md`
- Overall progress: See `docs/PROJECT-STATUS.md`

---

**Last Updated**: 2025-01-25
**Version**: 2.0
**Status**: Deployment Readiness Phase (Phases 1-4,6 Complete)
