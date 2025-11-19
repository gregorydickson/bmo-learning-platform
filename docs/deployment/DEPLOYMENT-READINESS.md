# AWS Deployment Readiness Report
**Target Region:** us-east-2
**Generated:** 2025-11-16
**Application:** BMO Learning Platform

---

## Executive Summary

The BMO Learning Platform is a production-ready AI-powered microlearning system with the following components:
- **Python AI Service** (FastAPI, port 8000) - LangChain-based lesson generation
- **Rails API** (Rails 7.2.3, port 3000) - Business logic and orchestration
- **PostgreSQL** with pgvector - Primary database
- **Redis** - Caching and background jobs
- **Sidekiq** - Background job processor

**Status:** PARTIALLY READY - Missing critical Terraform infrastructure modules

---

## 1. Current Infrastructure Review

### 1.1 Existing Terraform Configuration

**Location:** `infrastructure/terraform/environments/prod/`

**What's Configured:**
- Backend: S3 state storage (bucket: `bmo-learning-terraform-state`)
- VPC Module: Complete with public/private subnets across 3 AZs (us-east-2a/b/c)
- ECS Module: Basic cluster with Fargate capacity providers
- Region: Properly set to us-east-2

**VPC Configuration:**
- CIDR: 10.0.0.0/16
- Public Subnets: 10.0.0.0/24, 10.0.1.0/24, 10.0.2.0/24
- Private Subnets: 10.0.10.0/24, 10.0.11.0/24, 10.0.12.0/24
- Internet Gateway: Configured
- NAT Gateways: MISSING (Critical for private subnet internet access)

**ECS Configuration:**
- Cluster Name: bmo-learning-prod
- Capacity Providers: Fargate, Fargate Spot
- Container Insights: Enabled
- CloudWatch Logs: Configured (/ecs/bmo-learning-prod, 30-day retention)

### 1.2 Missing Terraform Modules (BLOCKERS)

The following critical infrastructure components are NOT configured:

#### High Priority (Required for Deployment)
1. **RDS PostgreSQL Module**
   - Instance class: db.t3.medium (from tfvars.example)
   - Storage: 100GB
   - Multi-AZ: Required for production
   - pgvector extension: Required
   - Subnet group: Needs to use private subnets
   - Security group: Allow access from ECS tasks only

2. **ElastiCache Redis Module**
   - Node type: cache.t3.small (from tfvars.example)
   - Subnet group: Private subnets
   - Security group: Allow access from ECS tasks

3. **Application Load Balancer (ALB)**
   - Public-facing for HTTPS traffic
   - Target groups for ai_service (8000) and rails_api (3000)
   - SSL/TLS certificate from ACM
   - Health checks configured
   - Security groups for internet access

4. **ECS Task Definitions**
   - ai_service: 1024 CPU, 2048 MB memory
   - rails_api: 512 CPU, 1024 MB memory
   - sidekiq: 512 CPU, 1024 MB memory
   - Environment variables injection from Secrets Manager
   - IAM execution roles
   - CloudWatch log configuration

5. **ECS Services**
   - Service definitions for each task
   - Auto-scaling policies (1-10 tasks per service)
   - Load balancer integration
   - Service discovery (optional but recommended)

6. **ECR Repositories**
   - bmo-learning/ai-service
   - bmo-learning/rails-api
   - Lifecycle policies for image retention

7. **Security Groups**
   - ALB: Allow 80/443 from internet
   - ECS Tasks: Allow traffic from ALB, RDS, Redis
   - RDS: Allow 5432 from ECS tasks
   - Redis: Allow 6379 from ECS tasks

8. **IAM Roles and Policies**
   - ECS Task Execution Role: ECR pull, CloudWatch logs, Secrets Manager
   - ECS Task Role: S3 access, SES/SNS (for notifications)
   - Terraform execution role

9. **Secrets Manager**
   - Database credentials
   - OpenAI API key
   - Twilio credentials (optional)
   - Slack bot token (optional)
   - Application secrets

10. **NAT Gateways**
    - One per AZ (3 total) for high availability
    - Elastic IPs for each NAT gateway
    - Route table updates for private subnets

#### Medium Priority (Recommended)
11. **S3 Buckets**
    - Document storage
    - Backups
    - CloudWatch logs archival
    - Lifecycle policies

12. **CloudWatch Alarms**
    - ECS CPU/Memory utilization
    - RDS connections, storage, CPU
    - Redis memory usage
    - ALB 5xx errors, target health
    - Estimated costs

13. **Route53**
    - DNS records for application domain
    - SSL certificate validation

14. **WAF (Web Application Firewall)**
    - Rate limiting
    - SQL injection protection
    - XSS protection

#### Lower Priority (Nice to Have)
15. **CloudFront CDN**
16. **Auto-scaling Policies** (detailed)
17. **VPC Flow Logs**
18. **AWS Backup** plans

---

## 2. Environment Variables Check

### 2.1 Currently Configured (.env)
✅ AWS_ACCESS_KEY_ID (configured)
✅ AWS_SECRET_ACCESS_KEY (configured)
✅ AWS_REGION=us-east-2 (correct)
❌ OPENAI_API_KEY (empty - REQUIRED)
✅ OPENAI_MODEL (set to gpt-4-turbo-preview)
✅ DATABASE_URL (localhost - needs production value)
✅ REDIS_URL (localhost - needs production value)
✅ RAILS_ENV=development (needs to be 'production')
✅ PYTHON_ENV=development (needs to be 'production')
✅ LOG_LEVEL=INFO (appropriate)
❌ TWILIO_ACCOUNT_SID (empty - optional)
❌ TWILIO_AUTH_TOKEN (empty - optional)
❌ SLACK_BOT_TOKEN (empty - optional)

### 2.2 Production Environment Variables Needed

The following variables must be set via AWS Secrets Manager or ECS environment variables:

**Required:**
```bash
# OpenAI (CRITICAL)
OPENAI_API_KEY=sk-... # Must be set

# Database (will be RDS endpoint)
DATABASE_URL=postgresql://username:password@rds-endpoint:5432/bmo_learning_prod

# Redis (will be ElastiCache endpoint)
REDIS_URL=redis://elasticache-endpoint:6379/0

# Application Environment
RAILS_ENV=production
PYTHON_ENV=production
LOG_LEVEL=INFO

# AWS
AWS_REGION=us-east-2
```

**Optional (for full functionality):**
```bash
# External Services
TWILIO_ACCOUNT_SID=ACxxxx
TWILIO_AUTH_TOKEN=xxxx
SLACK_BOT_TOKEN=xoxb-xxxx

# LangChain Tracing (optional)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__xxxx
```

---

## 3. Docker Images Review

### 3.1 AI Service (Python/FastAPI)
**Dockerfile:** `app/ai_service/Dockerfile`

✅ Security: Non-root user (appuser, UID 1000)
✅ Multi-stage build potential
✅ Health check configured (GET /health)
✅ Minimal base image (python:3.11-slim)
⚠️  Dependency management: Uses `uv` (ensure compatible with AWS environment)

**Image size:** Not yet built - recommend testing locally first

### 3.2 Rails API
**Dockerfile:** `app/rails_api/Dockerfile`

✅ Security: Non-root user (appuser, UID 1000)
✅ Health check configured (GET /health)
✅ Minimal base image (ruby:3.2.2-slim)
✅ Standard bundler dependency management

**Note:** Same image used for both rails_api and sidekiq containers

### 3.3 Image Build & Push Strategy

Before deployment, you must:
1. Build both images locally
2. Tag with ECR repository URIs
3. Push to ECR
4. Update ECS task definitions with image URIs

**Commands (after ECR is created):**
```bash
# Login to ECR
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-2.amazonaws.com

# Build and push AI service
cd app/ai_service
docker build -t bmo-learning/ai-service:latest .
docker tag bmo-learning/ai-service:latest <account-id>.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/ai-service:latest
docker push <account-id>.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/ai-service:latest

# Build and push Rails API
cd ../rails_api
docker build -t bmo-learning/rails-api:latest .
docker tag bmo-learning/rails-api:latest <account-id>.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/rails-api:latest
docker push <account-id>.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/rails-api:latest
```

---

## 4. AWS Prerequisites

### 4.1 IAM Permissions Required

Your AWS user/role needs the following permissions to execute Terraform:

**Service Permissions:**
- EC2: Full (VPC, subnets, security groups, NAT gateways)
- ECS: Full (clusters, services, task definitions)
- ECR: Full (repositories)
- RDS: Full (DB instances, subnet groups, parameter groups)
- ElastiCache: Full (clusters, subnet groups, parameter groups)
- ELB: Full (ALBs, target groups, listeners)
- IAM: CreateRole, AttachRolePolicy, CreatePolicy
- CloudWatch: Logs, Alarms
- Secrets Manager: Full
- S3: Full (for state and app buckets)
- DynamoDB: Access for state locking
- Route53: Full (if using custom domain)
- ACM: Full (for SSL certificates)

**Terraform State Permissions:**
- S3 bucket: `bmo-learning-terraform-state` (read/write)
- DynamoDB table: `terraform-state-lock` (read/write)

### 4.2 AWS Resources to Create Before Terraform

**Must exist before running terraform apply:**

1. **S3 State Bucket** (may already exist)
   ```bash
   aws s3 mb s3://bmo-learning-terraform-state --region us-east-2
   aws s3api put-bucket-versioning --bucket bmo-learning-terraform-state --versioning-configuration Status=Enabled
   aws s3api put-bucket-encryption --bucket bmo-learning-terraform-state --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
   ```

2. **DynamoDB Lock Table** (may already exist)
   ```bash
   aws dynamodb create-table \
     --table-name terraform-state-lock \
     --attribute-definitions AttributeName=LockID,AttributeType=S \
     --key-schema AttributeName=LockID,KeyType=HASH \
     --billing-mode PAY_PER_REQUEST \
     --region us-east-2
   ```

3. **OpenAI API Key** (CRITICAL)
   - Obtain from https://platform.openai.com/api-keys
   - Store in AWS Secrets Manager before deployment

4. **Domain Name** (optional but recommended)
   - Register domain or use existing
   - Create hosted zone in Route53
   - Request ACM certificate for HTTPS

---

## 5. External Service Dependencies

### 5.1 Required Services
1. **OpenAI** (CRITICAL)
   - API Key required
   - Recommended models: GPT-4 Turbo, text-embedding-3-small
   - Estimated cost: $450-650/month for 900 learners
   - Rate limits: Check organization limits

### 5.2 Optional Services
2. **Twilio** (for SMS delivery)
   - Account SID and Auth Token
   - Phone number provisioning
   - Cost: Pay-per-message

3. **Slack** (for Slack message delivery)
   - Bot token (xoxb-)
   - Workspace installation
   - Required OAuth scopes: chat:write, users:read

4. **LangSmith** (for LangChain tracing)
   - API key from LangSmith
   - Set LANGCHAIN_TRACING_V2=true

---

## 6. Database Migration Strategy

### 6.1 Rails Migrations
**Location:** `app/rails_api/db/migrate/`

The application requires database schema setup. After RDS is provisioned:

```bash
# Run migrations
cd app/rails_api
RAILS_ENV=production bundle exec rails db:migrate

# Verify
RAILS_ENV=production bundle exec rails db:version
```

### 6.2 Vector Store (Chroma)
The Python AI service uses Chroma for vector embeddings. In production:
- May need persistent storage (EFS or S3)
- Initial document ingestion required
- Consider pre-loading during deployment

---

## 7. Cost Estimation

### 7.1 Infrastructure Costs (Monthly, us-east-2)

**Compute:**
- ECS Fargate (3 services, avg 2 tasks each): ~$260
- NAT Gateways (3 AZs): ~$100

**Data:**
- RDS PostgreSQL (db.t3.medium, Multi-AZ, 100GB): ~$180
- ElastiCache Redis (cache.t3.small): ~$50

**Networking:**
- ALB: ~$25
- Data transfer: ~$50

**Storage:**
- S3 (documents, backups): ~$20
- CloudWatch Logs: ~$10

**Total Infrastructure:** ~$695/month

**LLM Costs (OpenAI):**
- GPT-4 Turbo: ~$300-500/month
- Embeddings: ~$100/month
- Moderation: ~$50/month

**Grand Total:** ~$1,145-1,345/month (for 900 active learners)

### 7.2 Cost Optimization Strategies
- Reserved instances for RDS (save 40%)
- Fargate Spot for non-critical tasks (save 70%)
- Redis caching to reduce LLM calls (current: 60%+ cache hit rate)
- Lifecycle policies for S3 and CloudWatch logs

---

## 8. Pre-Deployment Checklist

### Phase 1: AWS Account Setup
- [ ] Verify AWS credentials are configured (✅ Already done)
- [ ] Create/verify S3 state bucket exists
- [ ] Create/verify DynamoDB lock table exists
- [ ] Obtain OpenAI API key (CRITICAL)
- [ ] Store secrets in AWS Secrets Manager
- [ ] Request ACM certificate (if using custom domain)

### Phase 2: Terraform Infrastructure (BLOCKERS)
- [ ] Create RDS Terraform module
- [ ] Create ElastiCache Terraform module
- [ ] Create ALB Terraform module
- [ ] Create Security Groups module
- [ ] Create NAT Gateway configuration
- [ ] Create ECR Terraform module
- [ ] Create ECS Task Definitions module
- [ ] Create ECS Services module
- [ ] Create IAM Roles module
- [ ] Create Secrets Manager module
- [ ] Create S3 buckets module
- [ ] Create CloudWatch alarms module
- [ ] Update terraform.tfvars with production values
- [ ] Run `terraform plan` and review
- [ ] Run `terraform apply`

### Phase 3: Docker Images
- [ ] Test build AI service locally
- [ ] Test build Rails API locally
- [ ] Create ECR repositories (via Terraform or manually)
- [ ] Build and tag production images
- [ ] Push images to ECR
- [ ] Verify images in ECR console

### Phase 4: Database Setup
- [ ] Wait for RDS to be available
- [ ] Update DATABASE_URL in Secrets Manager
- [ ] Run Rails migrations
- [ ] Verify database schema
- [ ] Seed initial data (if needed)

### Phase 5: Application Configuration
- [ ] Update all environment variables in ECS task definitions
- [ ] Configure CORS allowed origins
- [ ] Set up CloudWatch log groups
- [ ] Configure health check endpoints
- [ ] Test service connectivity (VPC, security groups)

### Phase 6: Deployment
- [ ] Deploy ECS services
- [ ] Verify tasks are running
- [ ] Check CloudWatch logs for errors
- [ ] Test health endpoints
- [ ] Test application functionality
- [ ] Configure auto-scaling policies
- [ ] Set up CloudWatch alarms
- [ ] Configure backup strategies

### Phase 7: Post-Deployment
- [ ] Load test the application
- [ ] Monitor costs in AWS Cost Explorer
- [ ] Set up budget alerts
- [ ] Document deployment process
- [ ] Create runbooks for common operations
- [ ] Set up monitoring dashboards
- [ ] Configure alerting (PagerDuty, etc.)

---

## 9. Critical Blockers Summary

**CANNOT DEPLOY UNTIL THESE ARE RESOLVED:**

1. **Missing Terraform Modules** (Priority 1)
   - RDS PostgreSQL
   - ElastiCache Redis
   - Application Load Balancer
   - NAT Gateways
   - Security Groups
   - ECR Repositories
   - ECS Task Definitions
   - ECS Services
   - IAM Roles
   - Secrets Manager

2. **OpenAI API Key** (Priority 1)
   - Required for core functionality
   - Must be obtained and stored in Secrets Manager

3. **Docker Images** (Priority 1)
   - Must be built and pushed to ECR before ECS deployment

4. **Environment Variables** (Priority 2)
   - Production values needed for DATABASE_URL, REDIS_URL
   - RAILS_ENV and PYTHON_ENV must be set to 'production'

---

## 10. Recommended Next Steps

### Immediate (Today)
1. **Obtain OpenAI API Key** - Go to https://platform.openai.com/api-keys
2. **Create missing Terraform modules** - Start with RDS, ElastiCache, ALB
3. **Verify S3 state bucket and DynamoDB table exist**

### Short Term (This Week)
4. **Complete all Terraform infrastructure modules**
5. **Build and test Docker images locally**
6. **Run `terraform plan` to verify configuration**
7. **Create Secrets Manager secrets**

### Medium Term (Next Week)
8. **Deploy infrastructure with `terraform apply`**
9. **Push Docker images to ECR**
10. **Run database migrations**
11. **Deploy ECS services**
12. **Perform integration testing**

### Long Term (Within Month)
13. **Set up monitoring and alerting**
14. **Load test the application**
15. **Document operational procedures**
16. **Create disaster recovery plan**

---

## 11. Architecture Diagram

```
Internet
   │
   ▼
[ALB - Public Subnets]
   │
   ├──────────────────┬──────────────────┐
   ▼                  ▼                  ▼
[ECS: AI Service] [ECS: Rails API] [ECS: Sidekiq]
   │                  │                  │
   └──────────────────┴──────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
    [RDS PG]      [Redis]        [S3]
   (Private)     (Private)    (Documents)
```

**Network Flow:**
1. Internet → ALB (HTTPS:443)
2. ALB → ECS Tasks (HTTP:8000, HTTP:3000)
3. ECS Tasks → RDS (PostgreSQL:5432)
4. ECS Tasks → Redis (6379)
5. ECS Tasks → S3 (Documents)
6. ECS Tasks → Internet (via NAT Gateway for OpenAI API calls)

---

## 12. Support Resources

**AWS Documentation:**
- [ECS on Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)
- [RDS PostgreSQL](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
- [ElastiCache Redis](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/)
- [Application Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/)

**Application Documentation:**
- See `CODEBASE-OVERVIEW.md` for architecture details
- See `DEPLOYMENT-SUMMARY.md` for quick reference
- See `AWS-DEPLOYMENT-GUIDE.md` for step-by-step deployment

---

**Report Status:** Ready for review
**Prepared by:** Atlas (AI Assistant)
**Date:** 2025-11-16
