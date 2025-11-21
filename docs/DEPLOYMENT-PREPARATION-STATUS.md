# Deployment Preparation Status

**Date**: 2025-11-21
**Account ID**: 840285932802
**Region**: us-east-2
**Environment**: Production (Demo Configuration)

---

## ✅ Completed Steps

### 1. S3 Backend Configuration
- **Status**: ✅ Complete
- **Bucket**: `bmo-learning-terraform-state`
- **Features**:
  - Versioning enabled
  - AES256 encryption enabled
  - Ready for Terraform state storage

### 2. DynamoDB State Locking
- **Status**: ✅ Complete
- **Table**: `terraform-state-lock`
- **Configuration**:
  - Billing mode: PAY_PER_REQUEST
  - Status: ACTIVE
  - Ready for state locking

### 3. Terraform Initialization
- **Status**: ✅ Complete
- **Backend**: S3 (configured)
- **Providers**: AWS v5.100.0, Random v3.7.2
- **Modules**: All initialized

### 4. ECR Repositories
- **Status**: ✅ Already exist
- **AI Service**: `840285932802.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/ai-service`
- **Rails API**: `840285932802.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/rails-api`

### 5. Cost Optimizations
- **Status**: ✅ Implemented
- **Savings**: $83-85/month (60% reduction)
- **Changes**:
  - Eliminated NAT Gateway ($32/month saved)
  - Reduced Fargate sizes ($46/month saved)
  - Migrated to Aurora Serverless v2 ($10/month saved)

---

## 🔄 In Progress

### Docker Image Builds
- **AI Service**: Building (downloading Python dependencies)
- **Rails API**: Building in parallel

---

## 📋 Remaining Steps

### Next Actions
1. ⏳ Wait for Docker builds to complete
2. ⏳ Login to ECR
3. ⏳ Tag images with ECR repository URLs
4. ⏳ Push images to ECR
5. ⏳ Update terraform.tfvars with image URIs
6. ⏳ Run terraform plan
7. ⏳ Review and approve infrastructure changes
8. ⏳ Run terraform apply

### Post-Deployment Actions
1. Set API keys in AWS Secrets Manager:
   - Anthropic API key (required)
   - OpenAI API key (required for embeddings)
   - Twilio credentials (optional)
   - Slack bot token (optional)

2. Force ECS service redeployment to pick up secrets

3. Run database migrations:
   ```bash
   aws ecs execute-command --cluster bmo-learning-prod \
     --task <task-id> --container rails-api \
     --command "bundle exec rails db:migrate" --interactive
   ```

4. Test endpoints:
   - AI Service health: `http://<alb-dns>/health`
   - Rails API health: `http://<alb-dns>/api/v1/health`

---

## Infrastructure Summary

### Current Terraform State
- **VPC**: vpc-0368be6b4c2be1dc5
- **ECS Cluster**: bmo-learning-prod
- **S3 Buckets**:
  - Documents: bmo-learning-prod-documents
  - Backups: bmo-learning-prod-backups

### Resources to be Created
- Aurora Serverless v2 cluster (0.5-2 ACU)
- ElastiCache Redis (cache.t3.micro)
- Application Load Balancer
- ECS Services (AI Service, Rails API, Sidekiq)
- Security Groups
- IAM Roles
- Secrets Manager secrets

### Cost-Optimized Configuration
| Resource | Configuration | Monthly Cost |
|----------|--------------|--------------|
| Fargate Tasks | 3 tasks (minimal sizes) | ~$24 |
| Aurora Serverless v2 | 0.5-2 ACU | ~$10 |
| Redis | cache.t3.micro | ~$12 |
| ALB | Standard | ~$25 |
| Data Transfer | ~10GB | ~$5 |
| CloudWatch Logs | ~5GB | ~$5 |
| S3 + ECR | <3GB | ~$1.50 |
| **Total Infrastructure** | | **~$52.50** |
| **API Costs** | Anthropic + OpenAI | **~$2-3** |
| **Grand Total** | | **~$55/month** |

---

## ECR Image URIs (To be updated in terraform.tfvars)

```hcl
# Update these in terraform.tfvars after pushing images
ai_service_image = "840285932802.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/ai-service:latest"
rails_api_image  = "840285932802.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/rails-api:latest"
```

---

## Deployment Timeline (Estimated)

| Phase | Duration | Status |
|-------|----------|--------|
| S3/DynamoDB Setup | 5 min | ✅ Complete |
| ECR Repository Creation | 2 min | ✅ Complete |
| Docker Builds | 10-15 min | 🔄 In Progress |
| Push to ECR | 5 min | ⏳ Pending |
| Terraform Plan | 2 min | ⏳ Pending |
| Terraform Apply | 20-30 min | ⏳ Pending |
| Secrets Configuration | 5 min | ⏳ Pending |
| ECS Deployment | 10 min | ⏳ Pending |
| Testing | 10 min | ⏳ Pending |
| **Total** | **~70-85 min** | **20% Complete** |

---

## Required Secrets

### Must be Set Before First Request
```bash
# Anthropic API Key
aws secretsmanager put-secret-value \
  --secret-id bmo-learning/prod/anthropic-api-key \
  --secret-string "sk-ant-YOUR_KEY" \
  --region us-east-2

# OpenAI API Key (for embeddings)
aws secretsmanager put-secret-value \
  --secret-id bmo-learning/prod/openai-api-key \
  --secret-string "sk-YOUR_KEY" \
  --region us-east-2
```

### Optional (Can be set later)
- Twilio Account SID & Auth Token (for SMS delivery)
- Slack Bot Token (for Slack delivery)

---

## Validation Checklist

Before running `terraform apply`:

- [x] S3 backend configured and versioned
- [x] DynamoDB lock table active
- [x] Terraform initialized with backend
- [x] ECR repositories exist
- [ ] Docker images built successfully
- [ ] Images pushed to ECR
- [ ] terraform.tfvars updated with image URIs
- [ ] terraform plan reviewed and approved
- [ ] API keys ready (Anthropic, OpenAI)

After deployment:

- [ ] All ECS services running (desired count = running count)
- [ ] Health endpoints return 200 OK
- [ ] Database migrations completed
- [ ] CloudWatch logs show no errors
- [ ] ALB target groups healthy
- [ ] Test API request successful

---

## Rollback Plan

If deployment fails:

1. **Terraform Issues**:
   ```bash
   terraform destroy -target=<failed-resource>
   ```

2. **Application Issues**:
   - Check CloudWatch logs for errors
   - Revert Docker image tags to previous version
   - Force new ECS deployment with old images

3. **Database Issues**:
   - Aurora Serverless scales automatically
   - Check security group rules
   - Verify secret values in Secrets Manager

4. **Complete Rollback**:
   ```bash
   terraform destroy
   # Fix issues, then redeploy
   ```

---

## Monitoring Post-Deployment

Key metrics to watch:

1. **ECS**:
   - CPU/Memory utilization
   - Task restart rate
   - Desired vs running count

2. **Aurora**:
   - ACU utilization
   - Connection count
   - Query performance

3. **ALB**:
   - Request count
   - Response time (p50, p95, p99)
   - 4xx/5xx error rates

4. **Costs**:
   - Daily AWS Cost Explorer
   - CloudWatch metrics for resource usage
   - Anthropic/OpenAI API usage

---

**Last Updated**: 2025-11-21 13:32 UTC
**Next Step**: Wait for Docker builds to complete, then push to ECR
**Estimated Completion**: ~1 hour
