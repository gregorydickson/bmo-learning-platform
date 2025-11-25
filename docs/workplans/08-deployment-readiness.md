# Phase 8: AWS Deployment Readiness

**Status**: In Progress (5/10 - Cost Optimization Complete, Deployment Blockers Remain)
**Priority**: CRITICAL - Immediate blockers must be resolved before deployment
**Note**: All cost optimizations are now complete ($68/month achieved)

---

## Overview

This workplan addresses the deployment readiness gaps identified by the architect assessment. The infrastructure code is largely complete with cost optimizations, but several critical blockers prevent immediate deployment.

**Architecture Context**:
- Cost-optimized demo configuration (~$55/month vs $665/month production)
- Aurora Serverless v2 for database (0.5-2 ACU scaling)
- Single-task ECS services (demo environment)
- Public subnet deployment (NAT Gateway eliminated for cost savings)

---

## Deployment Readiness Assessment

**Current State**: 4/10 - NOT READY

**Blockers**:
1. Docker images not built/pushed to ECR (PRIMARY BLOCKER)
2. Terraform state changes uncommitted
3. terraform.tfvars contains PLACEHOLDER image URIs
4. S3 state bucket existence unclear (may exist from previous work)
5. OpenAI/Anthropic API keys not set in AWS Secrets Manager

**Short-term Needs**:
- EFS volume for Chroma vector store persistence
- CloudWatch alarms for production monitoring
- Review and implement ULTRA-LOW-COST-AWS-OPTIMIZATION.md recommendations

**Medium-term Production Hardening**:
- WAF for ALB protection
- RDS automated backup configuration
- Circuit breaker pattern for inter-service calls

---

## Phase 1: Immediate Blockers (CRITICAL)

### 1. Commit Terraform Changes
- [ ] Review modified Terraform files
  - infrastructure/terraform/environments/prod/main.tf
  - infrastructure/terraform/modules/alb/main.tf
  - infrastructure/terraform/modules/rds/main.tf
- [ ] Create meaningful commit with cost optimization changes
- [ ] Push to main branch
- [ ] Remove stale .tfplan files from git tracking

**Files to add**:
```bash
git add infrastructure/terraform/
git commit -m "Infrastructure: Aurora Serverless v2 and cost optimizations"
```

**Files to clean up**:
```bash
rm infrastructure/terraform/environments/prod/phase1.tfplan
rm infrastructure/terraform/environments/prod/tfplan
```

### 2. Build and Push Docker Images to ECR
- [ ] Verify AWS credentials configured
  ```bash
  aws sts get-caller-identity
  ```
- [ ] Authenticate Docker to ECR
  ```bash
  aws ecr get-login-password --region us-east-2 | \
    docker login --username AWS --password-stdin 840285932802.dkr.ecr.us-east-2.amazonaws.com
  ```
- [ ] Build AI Service image
  ```bash
  cd app/ai_service
  docker build -t bmo-learning/ai-service:latest .
  ```
- [ ] Tag AI Service image for ECR
  ```bash
  docker tag bmo-learning/ai-service:latest \
    840285932802.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/ai-service:latest
  ```
- [ ] Push AI Service image
  ```bash
  docker push 840285932802.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/ai-service:latest
  ```
- [ ] Build Rails API image
  ```bash
  cd app/rails_api
  docker build -t bmo-learning/rails-api:latest .
  ```
- [ ] Tag Rails API image for ECR
  ```bash
  docker tag bmo-learning/rails-api:latest \
    840285932802.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/rails-api:latest
  ```
- [ ] Push Rails API image
  ```bash
  docker push 840285932802.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/rails-api:latest
  ```
- [ ] Verify images exist in ECR
  ```bash
  aws ecr describe-images --repository-name bmo-learning/ai-service --region us-east-2
  aws ecr describe-images --repository-name bmo-learning/rails-api --region us-east-2
  ```

### 3. Update terraform.tfvars with Real ECR Image URIs
- [ ] Open infrastructure/terraform/environments/prod/terraform.tfvars
- [ ] Replace PLACEHOLDER_AI_SERVICE with actual URI
  ```hcl
  ai_service_image = "840285932802.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/ai-service:latest"
  ```
- [ ] Replace PLACEHOLDER_RAILS_API with actual URI
  ```hcl
  rails_api_image = "840285932802.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/rails-api:latest"
  ```
- [ ] Commit changes
  ```bash
  git add infrastructure/terraform/environments/prod/terraform.tfvars
  git commit -m "Infrastructure: Update ECR image URIs for deployment"
  ```

### 4. Verify S3 State Backend
- [ ] Check if S3 bucket exists
  ```bash
  aws s3 ls s3://bmo-learning-terraform-state --region us-east-2
  ```
- [ ] If bucket doesn't exist, create it
  ```bash
  aws s3 mb s3://bmo-learning-terraform-state --region us-east-2
  aws s3api put-bucket-versioning \
    --bucket bmo-learning-terraform-state \
    --versioning-configuration Status=Enabled \
    --region us-east-2
  aws s3api put-bucket-encryption \
    --bucket bmo-learning-terraform-state \
    --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}' \
    --region us-east-2
  ```
- [ ] Check if DynamoDB lock table exists
  ```bash
  aws dynamodb describe-table --table-name terraform-state-lock --region us-east-2
  ```
- [ ] If table doesn't exist, create it
  ```bash
  aws dynamodb create-table \
    --table-name terraform-state-lock \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-2
  ```

### 5. Prepare API Keys for Secrets Manager
- [ ] Locate Anthropic API key (if using Claude models)
- [ ] Locate OpenAI API key (required for embeddings)
- [ ] Document optional keys:
  - Twilio Account SID & Auth Token (for SMS delivery)
  - Slack Bot Token (for Slack delivery)
- [ ] Create secure note with all keys for deployment phase

**Note**: Keys will be set in Secrets Manager AFTER infrastructure deployment (Phase 3, Task 7).

---

## Phase 2: Terraform Deployment

### 6. Initialize Terraform
- [ ] Navigate to production environment
  ```bash
  cd infrastructure/terraform/environments/prod
  ```
- [ ] Initialize Terraform with backend
  ```bash
  terraform init
  ```
- [ ] Verify modules initialized
  ```bash
  terraform get
  ```
- [ ] Validate configuration
  ```bash
  terraform validate
  ```
- [ ] Format code
  ```bash
  terraform fmt -recursive
  ```

### 7. Plan Infrastructure Changes
- [ ] Run Terraform plan
  ```bash
  terraform plan -out=deployment.tfplan
  ```
- [ ] Review plan output carefully:
  - VPC and networking resources
  - Security groups (verify restrictive ingress rules)
  - Aurora Serverless v2 cluster (0.5-2 ACU configuration)
  - ElastiCache Redis (cache.t3.micro)
  - ALB with target groups
  - ECS cluster and services (1 task each)
  - IAM roles (ECS task execution and task roles)
  - Secrets Manager secrets (empty placeholders)
  - S3 buckets (documents and backups)
- [ ] Verify cost estimate aligns with ~$55/month projection
- [ ] Document any unexpected resources or deletions

### 8. Apply Infrastructure
- [ ] Run Terraform apply
  ```bash
  terraform apply deployment.tfplan
  ```
- [ ] Monitor progress (Aurora takes 15-20 minutes)
- [ ] Note any errors or warnings
- [ ] Capture outputs
  ```bash
  terraform output > deployment-outputs.txt
  ```
- [ ] Save ALB DNS name for testing
  ```bash
  terraform output alb_dns_name
  ```

### 9. Verify Infrastructure Deployment
- [ ] Check VPC exists
  ```bash
  aws ec2 describe-vpcs --filters "Name=tag:Name,Values=bmo-learning-prod" --region us-east-2
  ```
- [ ] Check Aurora cluster status (should be "available")
  ```bash
  aws rds describe-db-clusters --db-cluster-identifier bmo-learning-prod --region us-east-2
  ```
- [ ] Check Redis cluster status (should be "available")
  ```bash
  aws elasticache describe-cache-clusters --cache-cluster-id bmo-learning-prod --region us-east-2
  ```
- [ ] Check ECS cluster
  ```bash
  aws ecs describe-clusters --clusters bmo-learning-prod --region us-east-2
  ```
- [ ] Check ECS services exist (ai-service, rails-api, sidekiq)
  ```bash
  aws ecs list-services --cluster bmo-learning-prod --region us-east-2
  ```
- [ ] Check ALB target groups (should have unhealthy targets initially)
  ```bash
  aws elbv2 describe-target-health --target-group-arn <arn-from-outputs> --region us-east-2
  ```

---

## Phase 3: Application Configuration

### 10. Set Secrets in AWS Secrets Manager
- [ ] Set Anthropic API key
  ```bash
  aws secretsmanager put-secret-value \
    --secret-id bmo-learning/prod/anthropic-api-key \
    --secret-string "sk-ant-YOUR_KEY" \
    --region us-east-2
  ```
- [ ] Set OpenAI API key (required for embeddings)
  ```bash
  aws secretsmanager put-secret-value \
    --secret-id bmo-learning/prod/openai-api-key \
    --secret-string "sk-YOUR_KEY" \
    --region us-east-2
  ```
- [ ] Optionally set Twilio credentials
  ```bash
  aws secretsmanager put-secret-value \
    --secret-id bmo-learning/prod/twilio-account-sid \
    --secret-string "YOUR_SID" \
    --region us-east-2
  aws secretsmanager put-secret-value \
    --secret-id bmo-learning/prod/twilio-auth-token \
    --secret-string "YOUR_TOKEN" \
    --region us-east-2
  ```
- [ ] Optionally set Slack bot token
  ```bash
  aws secretsmanager put-secret-value \
    --secret-id bmo-learning/prod/slack-bot-token \
    --secret-string "xoxb-YOUR_TOKEN" \
    --region us-east-2
  ```
- [ ] Verify secrets exist
  ```bash
  aws secretsmanager list-secrets --region us-east-2 | grep bmo-learning
  ```

### 11. Force ECS Service Redeployment
- [ ] Redeploy AI Service to pick up secrets
  ```bash
  aws ecs update-service \
    --cluster bmo-learning-prod \
    --service ai-service \
    --force-new-deployment \
    --region us-east-2
  ```
- [ ] Redeploy Rails API
  ```bash
  aws ecs update-service \
    --cluster bmo-learning-prod \
    --service rails-api \
    --force-new-deployment \
    --region us-east-2
  ```
- [ ] Redeploy Sidekiq
  ```bash
  aws ecs update-service \
    --cluster bmo-learning-prod \
    --service sidekiq \
    --force-new-deployment \
    --region us-east-2
  ```
- [ ] Wait for services to stabilize (check ECS console)
  ```bash
  aws ecs wait services-stable \
    --cluster bmo-learning-prod \
    --services ai-service rails-api sidekiq \
    --region us-east-2
  ```

### 12. Run Database Migrations
- [ ] Get running Rails API task ID
  ```bash
  aws ecs list-tasks \
    --cluster bmo-learning-prod \
    --service-name rails-api \
    --region us-east-2
  ```
- [ ] Enable ECS Exec on task (if not already enabled)
  ```bash
  # May need to update task definition with enableExecuteCommand: true
  ```
- [ ] Run migrations via ECS Exec
  ```bash
  aws ecs execute-command \
    --cluster bmo-learning-prod \
    --task <task-id> \
    --container rails-api \
    --command "bundle exec rails db:migrate" \
    --interactive \
    --region us-east-2
  ```
- [ ] Alternative: Run migrations via one-off task
  ```bash
  # If ECS Exec fails, create migration task in Terraform
  ```
- [ ] Verify migrations completed successfully

### 13. Seed Initial Data (Optional)
- [ ] Run database seeds if needed
  ```bash
  aws ecs execute-command \
    --cluster bmo-learning-prod \
    --task <task-id> \
    --container rails-api \
    --command "bundle exec rails db:seed" \
    --interactive \
    --region us-east-2
  ```
- [ ] Verify seed data in database

---

## Phase 4: Verification and Testing

### 14. Health Check Verification
- [ ] Get ALB DNS name
  ```bash
  terraform output alb_dns_name
  ```
- [ ] Test AI Service health endpoint
  ```bash
  curl http://<alb-dns>/health
  # Expected: {"status":"healthy","service":"ai-service"}
  ```
- [ ] Test Rails API health endpoint
  ```bash
  curl http://<alb-dns>/api/v1/health
  # Expected: {"status":"ok","database":"connected","redis":"connected"}
  ```
- [ ] Check ALB target group health
  ```bash
  aws elbv2 describe-target-health \
    --target-group-arn <ai-service-tg-arn> \
    --region us-east-2
  aws elbv2 describe-target-health \
    --target-group-arn <rails-api-tg-arn> \
    --region us-east-2
  ```
- [ ] Verify all targets are "healthy"

### 15. CloudWatch Logs Review
- [ ] View AI Service logs
  ```bash
  aws logs tail /ecs/bmo-learning-prod/ai-service --follow --region us-east-2
  ```
- [ ] Check for errors or warnings
- [ ] View Rails API logs
  ```bash
  aws logs tail /ecs/bmo-learning-prod/rails-api --follow --region us-east-2
  ```
- [ ] Check for errors or warnings
- [ ] View Sidekiq logs
  ```bash
  aws logs tail /ecs/bmo-learning-prod/sidekiq --follow --region us-east-2
  ```
- [ ] Verify Sidekiq connected to Redis and processing jobs

### 16. End-to-End API Testing
- [ ] Test lesson generation endpoint (requires valid learner)
  ```bash
  # May need to create test learner first
  curl -X POST http://<alb-dns>/api/v1/learners \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","name":"Test User"}'
  ```
- [ ] Request a lesson
  ```bash
  curl -X POST http://<alb-dns>/api/v1/learners/<learner-id>/request_lesson \
    -H "Content-Type: application/json" \
    -d '{"topic":"Python basics","difficulty":"beginner"}'
  ```
- [ ] Verify lesson generation via CloudWatch Logs
- [ ] Check Sidekiq processed background job
- [ ] Verify lesson stored in database

### 17. Performance Baseline
- [ ] Record AI Service response time (p50, p95, p99)
- [ ] Record Rails API response time
- [ ] Check Aurora ACU utilization (should be near 0.5 ACU idle)
  ```bash
  aws cloudwatch get-metric-statistics \
    --namespace AWS/RDS \
    --metric-name ServerlessDatabaseCapacity \
    --dimensions Name=DBClusterIdentifier,Value=bmo-learning-prod \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 300 \
    --statistics Average \
    --region us-east-2
  ```
- [ ] Check ECS task CPU/memory utilization
  ```bash
  aws cloudwatch get-metric-statistics \
    --namespace AWS/ECS \
    --metric-name CPUUtilization \
    --dimensions Name=ServiceName,Value=ai-service Name=ClusterName,Value=bmo-learning-prod \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 300 \
    --statistics Average \
    --region us-east-2
  ```
- [ ] Document baseline metrics for future comparison

---

## Phase 5: Short-Term Improvements

### 18. EFS Volume for Chroma Persistence
- [ ] Create EFS filesystem for Chroma vector store
  ```bash
  # Terraform module: infrastructure/terraform/modules/efs
  ```
- [ ] Mount EFS to AI Service task
  ```hcl
  # Update task definition with volume mount
  volume {
    name = "chroma-data"
    efs_volume_configuration {
      file_system_id = aws_efs_file_system.chroma.id
      root_directory = "/chroma"
    }
  }
  ```
- [ ] Update AI Service to use EFS path for Chroma persistence
  ```python
  # app/ai_service/config/settings.py
  CHROMA_PERSIST_DIRECTORY = "/mnt/efs/chroma"
  ```
- [ ] Apply Terraform changes
- [ ] Redeploy AI Service
- [ ] Verify Chroma data persists across task restarts

### 19. CloudWatch Alarms
- [ ] Create alarm for Aurora high ACU utilization (> 1.5 ACU for 5 minutes)
  ```bash
  aws cloudwatch put-metric-alarm \
    --alarm-name bmo-learning-prod-aurora-high-acu \
    --alarm-description "Aurora ACU above 1.5 for 5 minutes" \
    --metric-name ServerlessDatabaseCapacity \
    --namespace AWS/RDS \
    --statistic Average \
    --period 300 \
    --threshold 1.5 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 1 \
    --dimensions Name=DBClusterIdentifier,Value=bmo-learning-prod \
    --region us-east-2
  ```
- [ ] Create alarm for ECS service task count (< 1 task)
  ```bash
  aws cloudwatch put-metric-alarm \
    --alarm-name bmo-learning-prod-ai-service-low-tasks \
    --metric-name RunningTaskCount \
    --namespace ECS/ContainerInsights \
    --statistic Average \
    --period 60 \
    --threshold 1 \
    --comparison-operator LessThanThreshold \
    --evaluation-periods 2 \
    --dimensions Name=ServiceName,Value=ai-service Name=ClusterName,Value=bmo-learning-prod \
    --region us-east-2
  ```
- [ ] Create alarm for ALB 5xx errors (> 10 in 5 minutes)
  ```bash
  aws cloudwatch put-metric-alarm \
    --alarm-name bmo-learning-prod-alb-5xx-errors \
    --metric-name HTTPCode_Target_5XX_Count \
    --namespace AWS/ApplicationELB \
    --statistic Sum \
    --period 300 \
    --threshold 10 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 1 \
    --dimensions Name=LoadBalancer,Value=<alb-arn-suffix> \
    --region us-east-2
  ```
- [ ] Configure SNS topic for alarm notifications
  ```bash
  aws sns create-topic --name bmo-learning-prod-alarms --region us-east-2
  aws sns subscribe --topic-arn <topic-arn> --protocol email --notification-endpoint your-email@example.com
  ```
- [ ] Update alarms to publish to SNS topic

### 20. Review and Implement Ultra-Low-Cost Optimizations
- [x] Read docs/ULTRA-LOW-COST-AWS-OPTIMIZATION.md
- [x] NAT Gateway elimination (PREVIOUSLY IMPLEMENTED)
  - Cost savings: $32/month
  - ECS tasks deployed to public subnets with assign_public_ip = true
  - Security groups still protect all resources
- [x] Aurora Serverless v2 configuration (PREVIOUSLY IMPLEMENTED)
  - Confirmed: min_capacity = 0.5 ACU, max_capacity = 2 ACU
  - Savings: $9/month vs db.t3.micro
- [x] Replace ALB with NLB (IMPLEMENTED)
  - Cost savings: $7/month
  - Created new nlb module at infrastructure/terraform/modules/nlb/main.tf
  - Updated main.tf to use module.nlb instead of module.alb
  - NLB forwards all traffic to Rails API on port 3000
- [x] Optimize Fargate task sizes (IMPLEMENTED)
  - Updated main.tf variable defaults:
    - AI Service: 256 CPU / 512 MB
    - Rails API: 128 CPU / 256 MB
    - Sidekiq: 128 CPU / 256 MB
  - Savings: $52.50/month
- [x] Consolidate Rails + Sidekiq into single task (IMPLEMENTED)
  - Rails task definition now contains both Rails API and Sidekiq containers
  - Combined task size: 256 CPU / 512 MB (sum of individual allocations)
  - Removed separate Sidekiq task definition and ECS service
  - Savings: $8.75/month
- [x] Downgrade Redis to cache.t3.micro (IMPLEMENTED)
  - Updated redis_node_type variable in main.tf
  - Savings: $9/month
- [x] Reduce CloudWatch log retention to 3 days (IMPLEMENTED)
  - Updated all 3 log groups in ecs_services module
  - Savings: $3/month
- [x] Document final cost optimization decisions
  - All optimizations documented in ULTRA-LOW-COST-AWS-OPTIMIZATION.md
  - Final cost: $67.50/month (51% reduction from $139/month baseline)

---

## Phase 6: Medium-Term Production Hardening

### 21. WAF for ALB Protection
- [ ] Create WAF web ACL
  ```bash
  # Terraform module: infrastructure/terraform/modules/waf
  ```
- [ ] Add rate limiting rules (100 requests/5 minutes per IP)
- [ ] Add SQL injection protection
- [ ] Add XSS protection
- [ ] Associate WAF with ALB
- [ ] Test WAF rules with curl

### 22. RDS Automated Backups
- [ ] Verify backup retention period set (7-30 days)
  ```bash
  aws rds describe-db-clusters \
    --db-cluster-identifier bmo-learning-prod \
    --query 'DBClusters[0].BackupRetentionPeriod' \
    --region us-east-2
  ```
- [ ] Configure backup window (3:00-4:00 AM UTC)
- [ ] Enable automated snapshots
- [ ] Create manual snapshot for baseline
  ```bash
  aws rds create-db-cluster-snapshot \
    --db-cluster-snapshot-identifier bmo-learning-prod-baseline-2025-01-21 \
    --db-cluster-identifier bmo-learning-prod \
    --region us-east-2
  ```
- [ ] Document snapshot retention policy

### 23. Circuit Breaker Pattern for Service Calls
- [ ] Install circuit breaker gem in Rails
  ```ruby
  # Gemfile
  gem 'circuitbox'
  ```
- [ ] Configure circuit breaker for AI service calls
  ```ruby
  # app/rails_api/config/initializers/circuitbox.rb
  Circuitbox.configure do |config|
    config.default_circuit_store = Circuitbox::MemoryStore.new
  end
  ```
- [ ] Wrap AI service HTTP calls with circuit breaker
  ```ruby
  # app/rails_api/app/services/lesson_generation_service.rb
  circuit = Circuitbox.circuit(:ai_service, exceptions: [HTTParty::Error])
  circuit.run do
    HTTParty.post("#{ENV['AI_SERVICE_URL']}/api/v1/generate-lesson", ...)
  end
  ```
- [ ] Add fallback behavior when circuit is open
- [ ] Test circuit breaker by simulating AI service failure
- [ ] Monitor circuit breaker state in logs

### 24. Cost Monitoring and Alerts
- [ ] Create AWS Budget for $100/month threshold
  ```bash
  aws budgets create-budget \
    --account-id 840285932802 \
    --budget file://budget-config.json \
    --notifications-with-subscribers file://notifications.json
  ```
- [ ] Set up daily cost report email
- [ ] Create CloudWatch dashboard for cost metrics
- [ ] Document monthly cost tracking process

---

## Definition of Done

**Phase 1 (Immediate Blockers)**:
- [ ] All Terraform changes committed to git
- [ ] Docker images built and pushed to ECR
- [ ] terraform.tfvars updated with real ECR URIs
- [ ] S3 state backend verified/created
- [ ] API keys ready for Secrets Manager

**Phase 2 (Terraform Deployment)**:
- [ ] Terraform initialized and validated
- [ ] Terraform plan reviewed and approved
- [ ] Infrastructure deployed successfully
- [ ] All AWS resources verified as "available"

**Phase 3 (Application Configuration)**:
- [ ] Secrets set in AWS Secrets Manager
- [ ] ECS services redeployed with secrets
- [ ] Database migrations completed
- [ ] Seed data loaded (if applicable)

**Phase 4 (Verification)**:
- [ ] Health endpoints return 200 OK
- [ ] ALB target groups healthy
- [ ] CloudWatch logs show no critical errors
- [ ] End-to-end API test successful
- [ ] Performance baseline documented

**Phase 5 (Short-Term Improvements)**:
- [ ] EFS volume created and mounted (if needed)
- [ ] CloudWatch alarms configured
- [ ] Ultra-low-cost optimizations reviewed and decisions documented

**Phase 6 (Production Hardening)**:
- [ ] WAF configured and tested
- [ ] RDS automated backups enabled
- [ ] Circuit breaker implemented and tested
- [ ] Cost monitoring and alerts configured

---

## Risk Management

### High-Risk Items
| Risk | Impact | Mitigation |
|------|--------|------------|
| Aurora Serverless v2 cold start latency | Slow first request after idle period | Keep min_capacity at 0.5 ACU (no cold starts) |
| ECS tasks in public subnets | Security concern | Security groups restrict all inbound except ALB |
| Single task per service | No redundancy | Auto-scaling configured to launch new tasks on failure |
| Missing API keys | Services fail to start | Verify keys before deployment, monitor CloudWatch logs |

### Medium-Risk Items
| Risk | Impact | Mitigation |
|------|--------|------------|
| Chroma data not persisting | Vector store reset on task restart | Implement EFS volume in Phase 5 |
| No circuit breaker | Cascading failures if AI service down | Implement in Phase 6 |
| No WAF | Vulnerable to DDoS and injection attacks | Implement in Phase 6 |

---

## Rollback Plan

If deployment fails at any phase:

1. **Terraform Issues**:
   ```bash
   cd infrastructure/terraform/environments/prod
   terraform destroy -target=<failed-resource>
   # Fix issue, then re-apply
   ```

2. **ECS Service Issues**:
   - Check CloudWatch logs for errors
   - Verify secrets in Secrets Manager
   - Redeploy with corrected configuration
   ```bash
   aws ecs update-service --cluster bmo-learning-prod --service <service-name> --force-new-deployment
   ```

3. **Database Issues**:
   - Check Aurora cluster status
   - Verify security group allows ECS task ingress
   - Verify database credentials in Secrets Manager
   - Restore from snapshot if corrupted
   ```bash
   aws rds restore-db-cluster-from-snapshot \
     --db-cluster-identifier bmo-learning-prod-restore \
     --snapshot-identifier <snapshot-id>
   ```

4. **Complete Rollback**:
   ```bash
   terraform destroy
   # Fix all issues, then re-deploy from Phase 1
   ```

---

## Success Metrics

**Deployment Success**:
- [ ] All 3 ECS services running (desired count = running count)
- [ ] ALB health checks passing for all target groups
- [ ] Health endpoints return 200 OK
- [ ] Successful lesson generation via API
- [ ] CloudWatch logs show normal operation
- [ ] Infrastructure cost ≤ $60/month (first month)

**Performance Baseline**:
- [ ] AI Service p95 response time < 5 seconds
- [ ] Rails API p95 response time < 500ms
- [ ] Aurora idle ACU ~0.5 (minimal cost)
- [ ] ECS task CPU utilization < 50% under normal load

**Cost Validation**:
- [ ] AWS Cost Explorer shows daily spend ≤ $2/day
- [ ] No unexpected resources consuming cost
- [ ] Aurora ACU staying within 0.5-2 range

---

## Next Steps After Deployment

1. **Documentation**:
   - Update TERRAFORM-DEPLOYMENT-GUIDE.md with actual deployment experience
   - Document any issues encountered and resolutions
   - Create deployment runbook for future deployments

2. **Monitoring Setup**:
   - Create CloudWatch dashboard for key metrics
   - Set up log insights queries for common debugging
   - Configure LangSmith/observability tools for LLM tracing

3. **Client Demo Preparation**:
   - Prepare demo script with example API calls
   - Create demo video showing platform capabilities
   - Document architecture for client presentation

4. **Security Hardening**:
   - Run security scan on deployed infrastructure
   - Review IAM policies for least privilege
   - Enable GuardDuty for threat detection

---

**Last Updated**: 2025-01-25
**Version**: 1.0
**Status**: Ready to Execute
