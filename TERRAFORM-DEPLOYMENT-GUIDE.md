# Terraform Deployment Guide
**BMO Learning Platform - AWS us-east-2 Deployment**

---

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Phase 1: Pre-Deployment Setup](#phase-1-pre-deployment-setup)
4. [Phase 2: Build and Push Docker Images](#phase-2-build-and-push-docker-images)
5. [Phase 3: Terraform Deployment](#phase-3-terraform-deployment)
6. [Phase 4: Post-Deployment Configuration](#phase-4-post-deployment-configuration)
7. [Phase 5: Verification](#phase-5-verification)
8. [Troubleshooting](#troubleshooting)

---

## Overview

This guide walks you through deploying the BMO Learning Platform to AWS using the newly created Terraform modules.

**What Will Be Created:**
- ✅ VPC with 3 public and 3 private subnets across 3 AZs
- ✅ NAT Gateways (3) for outbound internet access
- ✅ Application Load Balancer (ALB)
- ✅ RDS PostgreSQL 16 (Multi-AZ, 100GB)
- ✅ ElastiCache Redis 7.1
- ✅ ECS Fargate Cluster with 3 services (AI, Rails, Sidekiq)
- ✅ ECR Repositories for Docker images
- ✅ S3 Buckets for documents and backups
- ✅ Secrets Manager for sensitive data
- ✅ IAM Roles and Security Groups
- ✅ CloudWatch Log Groups
- ✅ Auto-scaling for ECS services

---

## Prerequisites

### 1. Tools Required
```bash
# Verify installations
terraform --version  # Should be >= 1.5.0
aws --version        # AWS CLI v2
docker --version     # Docker 20.10+
```

### 2. AWS Credentials
Your AWS credentials are already configured in `.env`:
- AWS_ACCESS_KEY_ID: `AKIA4HJHRZUBJ5J3Q2OB`
- AWS_SECRET_ACCESS_KEY: (configured)
- AWS_REGION: `us-east-2`

Verify access:
```bash
aws sts get-caller-identity
```

### 3. OpenAI API Key
**CRITICAL**: Obtain OpenAI API key from https://platform.openai.com/api-keys

This is REQUIRED for the application to function.

---

## Phase 1: Pre-Deployment Setup

### Step 1.1: Create S3 State Bucket (if not exists)

```bash
# Check if bucket exists
aws s3 ls s3://bmo-learning-terraform-state 2>/dev/null

# If not found, create it
aws s3 mb s3://bmo-learning-terraform-state --region us-east-2

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket bmo-learning-terraform-state \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket bmo-learning-terraform-state \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

### Step 1.2: Create DynamoDB Lock Table (if not exists)

```bash
# Check if table exists
aws dynamodb describe-table --table-name terraform-state-lock --region us-east-2 2>/dev/null

# If not found, create it
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-2
```

### Step 1.3: Get AWS Account ID

```bash
# You'll need this for ECR image URLs
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "AWS Account ID: $AWS_ACCOUNT_ID"
```

---

## Phase 2: Build and Push Docker Images

### Step 2.1: Initialize Terraform (ECR Only)

We need ECR repositories before pushing images:

```bash
cd infrastructure/terraform/environments/prod

# Initialize Terraform
terraform init

# Create ONLY the ECR module first
terraform apply -target=module.ecr
```

This creates the ECR repositories.

### Step 2.2: Build Docker Images

```bash
# Navigate to project root
cd /Users/gregorydickson/learning-app

# Build AI Service
cd app/ai_service
docker build -t bmo-learning/ai-service:latest .

# Build Rails API
cd ../rails_api
docker build -t bmo-learning/rails-api:latest .

# Return to root
cd ../..
```

### Step 2.3: Login to ECR

```bash
aws ecr get-login-password --region us-east-2 | \
  docker login --username AWS --password-stdin \
  ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-2.amazonaws.com
```

### Step 2.4: Tag and Push Images

```bash
# Tag AI Service
docker tag bmo-learning/ai-service:latest \
  ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/ai-service:latest

# Push AI Service
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/ai-service:latest

# Tag Rails API
docker tag bmo-learning/rails-api:latest \
  ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/rails-api:latest

# Push Rails API
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/rails-api:latest
```

### Step 2.5: Update terraform.tfvars with Image URLs

```bash
cd infrastructure/terraform/environments/prod

# Edit terraform.tfvars
# Replace PLACEHOLDER_AI_SERVICE_IMAGE with:
# ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/ai-service:latest

# Replace PLACEHOLDER_RAILS_API_IMAGE with:
# ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/rails-api:latest
```

**Example:**
```hcl
ai_service_image = "123456789012.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/ai-service:latest"
rails_api_image  = "123456789012.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/rails-api:latest"
```

---

## Phase 3: Terraform Deployment

### Step 3.1: Review Terraform Plan

```bash
cd infrastructure/terraform/environments/prod

# Run terraform plan
terraform plan -out=tfplan

# Review the plan carefully
# Expected resources: ~60-70 resources to be created
```

**What to Check:**
- ✅ VPC and subnets in correct AZs
- ✅ RDS Multi-AZ enabled
- ✅ Security groups properly configured
- ✅ Image URLs are correct (not PLACEHOLDER)

### Step 3.2: Apply Terraform Configuration

```bash
# Apply the plan
terraform apply tfplan

# This will take 15-25 minutes
# RDS takes the longest (~15 minutes)
```

**Expected Timeline:**
- VPC, Subnets, IGW, NAT Gateways: 2-3 min
- Security Groups, IAM Roles: 1 min
- RDS PostgreSQL: 15-20 min (Multi-AZ)
- ElastiCache Redis: 5-8 min
- ALB: 2-3 min
- ECS Services: 3-5 min
- **Total: 20-30 minutes**

### Step 3.3: Capture Outputs

```bash
# After successful apply, get outputs
terraform output > ../../outputs.txt

# View important outputs
terraform output alb_dns_name
terraform output rds_endpoint
terraform output redis_endpoint
terraform output ecr_ai_service_repository_url
terraform output ecr_rails_api_repository_url
```

---

## Phase 4: Post-Deployment Configuration

### Step 4.1: Set OpenAI API Key in Secrets Manager

**CRITICAL STEP - Application will not work without this!**

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="sk-your-actual-openai-api-key-here"

# Update the secret in AWS Secrets Manager
aws secretsmanager put-secret-value \
  --secret-id bmo-learning/prod/openai-api-key \
  --secret-string "$OPENAI_API_KEY" \
  --region us-east-2

# Verify it was set
aws secretsmanager get-secret-value \
  --secret-id bmo-learning/prod/openai-api-key \
  --region us-east-2 \
  --query SecretString --output text
```

### Step 4.2: (Optional) Set External Service Credentials

If using Twilio or Slack:

```bash
# Twilio
aws secretsmanager put-secret-value \
  --secret-id bmo-learning/prod/twilio-account-sid \
  --secret-string "ACxxxxxxxxxxxx" \
  --region us-east-2

aws secretsmanager put-secret-value \
  --secret-id bmo-learning/prod/twilio-auth-token \
  --secret-string "your-twilio-auth-token" \
  --region us-east-2

# Slack
aws secretsmanager put-secret-value \
  --secret-id bmo-learning/prod/slack-bot-token \
  --secret-string "xoxb-your-slack-bot-token" \
  --region us-east-2
```

### Step 4.3: Run Database Migrations

The Rails application needs to create database tables:

```bash
# Get the ECS cluster and service names
CLUSTER_NAME=$(terraform output -raw ecs_cluster_name)
RAILS_SERVICE="bmo-learning-prod-rails-api"

# Get a running task ID
TASK_ARN=$(aws ecs list-tasks \
  --cluster $CLUSTER_NAME \
  --service-name $RAILS_SERVICE \
  --region us-east-2 \
  --query 'taskArns[0]' \
  --output text)

# Run migrations via ECS Exec
aws ecs execute-command \
  --cluster $CLUSTER_NAME \
  --task $TASK_ARN \
  --container rails-api \
  --interactive \
  --command "bundle exec rails db:migrate" \
  --region us-east-2
```

Alternative (if ECS Exec doesn't work):

```bash
# Create a one-off task to run migrations
# This requires updating the task definition with a migration command
# Simpler option: SSH into an EC2 bastion or use RDS Query Editor
```

### Step 4.4: Restart ECS Services (to pick up OpenAI key)

```bash
# Force new deployment to pick up the OpenAI API key
aws ecs update-service \
  --cluster bmo-learning-prod \
  --service bmo-learning-prod-ai-service \
  --force-new-deployment \
  --region us-east-2

aws ecs update-service \
  --cluster bmo-learning-prod \
  --service bmo-learning-prod-rails-api \
  --force-new-deployment \
  --region us-east-2

aws ecs update-service \
  --cluster bmo-learning-prod \
  --service bmo-learning-prod-sidekiq \
  --force-new-deployment \
  --region us-east-2
```

---

## Phase 5: Verification

### Step 5.1: Check ECS Service Status

```bash
# Check all services are running
aws ecs describe-services \
  --cluster bmo-learning-prod \
  --services \
    bmo-learning-prod-ai-service \
    bmo-learning-prod-rails-api \
    bmo-learning-prod-sidekiq \
  --region us-east-2 \
  --query 'services[*].[serviceName,desiredCount,runningCount,status]' \
  --output table
```

Expected output:
```
Service                       Desired  Running  Status
bmo-learning-prod-ai-service      2        2    ACTIVE
bmo-learning-prod-rails-api       2        2    ACTIVE
bmo-learning-prod-sidekiq         2        2    ACTIVE
```

### Step 5.2: Check ALB Target Health

```bash
# Get target group ARNs from outputs
terraform output | grep target_group

# Check target health
aws elbv2 describe-target-health \
  --target-group-arn <ai-service-target-group-arn> \
  --region us-east-2

aws elbv2 describe-target-health \
  --target-group-arn <rails-api-target-group-arn> \
  --region us-east-2
```

Expected: All targets should be "healthy"

### Step 5.3: Test Application Endpoints

```bash
# Get ALB DNS name
ALB_DNS=$(terraform output -raw alb_dns_name)

# Test Rails API health endpoint
curl http://$ALB_DNS/health

# Test AI Service health endpoint
curl http://$ALB_DNS/api/v1/generate-lesson

# Expected: {"status": "ok"} or similar
```

### Step 5.4: Check CloudWatch Logs

```bash
# View AI service logs
aws logs tail /ecs/bmo-learning-prod/ai-service \
  --follow \
  --region us-east-2

# View Rails API logs
aws logs tail /ecs/bmo-learning-prod/rails-api \
  --follow \
  --region us-east-2
```

Look for:
- ✅ No OpenAI API key errors
- ✅ Successful database connections
- ✅ Successful Redis connections

---

## Troubleshooting

### Issue: ECS Tasks Not Starting

**Check:**
```bash
# View task stopped reasons
aws ecs describe-tasks \
  --cluster bmo-learning-prod \
  --tasks <task-id> \
  --region us-east-2 \
  --query 'tasks[0].stoppedReason'
```

**Common Causes:**
- Docker image pull failed (check ECR repository policy)
- Secrets Manager permissions missing
- Health check failing

### Issue: "Cannot pull container image"

**Fix:**
```bash
# Ensure task execution role has ECR permissions
# Check IAM role: bmo-learning-prod-ecs-task-execution

# Re-push image
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/ai-service:latest
```

### Issue: Health Checks Failing

**Check:**
```bash
# Verify container is actually running
aws ecs execute-command \
  --cluster bmo-learning-prod \
  --task <task-id> \
  --container ai-service \
  --interactive \
  --command "/bin/sh"

# Inside container, test health endpoint
curl localhost:8000/health
```

### Issue: "OpenAI API Key Not Set"

**Fix:**
```bash
# Verify secret exists and has value
aws secretsmanager get-secret-value \
  --secret-id bmo-learning/prod/openai-api-key \
  --region us-east-2

# If empty, set it:
aws secretsmanager put-secret-value \
  --secret-id bmo-learning/prod/openai-api-key \
  --secret-string "sk-your-key" \
  --region us-east-2

# Restart services
aws ecs update-service --cluster bmo-learning-prod \
  --service bmo-learning-prod-ai-service \
  --force-new-deployment
```

### Issue: Database Connection Failed

**Check:**
```bash
# Verify RDS endpoint is accessible from ECS tasks
# Security group should allow port 5432 from ECS security group

# Get RDS endpoint
terraform output rds_endpoint

# Check security group rules
aws ec2 describe-security-groups \
  --group-ids <rds-security-group-id> \
  --region us-east-2
```

### Issue: Redis Connection Failed

**Check:**
```bash
# Similar to RDS, check security groups
terraform output redis_endpoint

# Verify ElastiCache is available
aws elasticache describe-replication-groups \
  --replication-group-id bmo-learning-prod \
  --region us-east-2 \
  --query 'ReplicationGroups[0].Status'
```

---

## Cleanup (Destroy Infrastructure)

**WARNING**: This will delete ALL resources and data!

```bash
cd infrastructure/terraform/environments/prod

# Disable deletion protection on RDS first
terraform apply -var="deletion_protection=false" -target=module.rds

# Destroy all resources
terraform destroy

# Confirm by typing 'yes'
```

**Note**: Some resources may need manual cleanup:
- S3 buckets (if they contain objects)
- CloudWatch log groups
- ECR images

---

## Cost Monitoring

After deployment, monitor costs:

```bash
# View current month costs
aws ce get-cost-and-usage \
  --time-period Start=$(date -u +"%Y-%m-01"),End=$(date -u +"%Y-%m-%d") \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE
```

**Expected Monthly Costs:**
- NAT Gateways (3): ~$100
- RDS db.t3.medium Multi-AZ: ~$180
- ElastiCache cache.t3.small: ~$50
- ECS Fargate (6 tasks avg): ~$260
- ALB: ~$25
- Data Transfer: ~$50
- **Total Infrastructure: ~$665/month**
- **OpenAI API: $450-650/month** (separate billing)

---

## Next Steps

After successful deployment:

1. **Set up Domain & SSL**
   - Register domain or use existing
   - Create ACM certificate
   - Update `acm_certificate_arn` in terraform.tfvars
   - Run `terraform apply`

2. **Configure Monitoring**
   - Set up CloudWatch Dashboards
   - Create alarms for high CPU, memory, errors
   - Configure SNS notifications

3. **Set up CI/CD**
   - GitHub Actions for automated deployments
   - Automatic image builds on push
   - Rolling deployments

4. **Load Test**
   - Test with expected load (900 learners)
   - Verify auto-scaling works
   - Tune resources if needed

5. **Backups**
   - Verify RDS automated backups working
   - Test RDS snapshot restore
   - Verify S3 lifecycle policies

---

## Support

**Issues?**
- Check CloudWatch Logs first
- Review ECS task stopped reasons
- Verify all secrets are set
- Check security group rules

**Documentation:**
- Terraform AWS Provider: https://registry.terraform.io/providers/hashicorp/aws/latest/docs
- ECS Best Practices: https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/
- RDS PostgreSQL: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html

---

**Deployment Status:** Ready for Production Deployment
**Last Updated:** 2025-11-16
**Infrastructure Version:** 1.0.0
