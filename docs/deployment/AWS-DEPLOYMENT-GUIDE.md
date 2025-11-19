# AWS Deployment Guide: us-east-2 Region

Quick Reference for Deploying BMO Learning Platform to AWS

---

## Pre-Deployment Checklist

### AWS Account Setup
- AWS account created with IAM user (AdministratorAccess or custom policy)
- AWS CLI configured: `aws configure --profile bmo-learning`
- Region set to `us-east-2`
- VPC quota checked (default: 5 VPCs per region)

### AWS Service Prerequisites

#### S3 for Terraform State
```bash
# Create terraform state bucket
aws s3 mb s3://bmo-learning-terraform-state --region us-east-2

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket bmo-learning-terraform-state \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket bmo-learning-terraform-state \
  --server-side-encryption-configuration file:///dev/stdin << 'JSON'
{
  "Rules": [
    {
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }
  ]
}
JSON
```

#### DynamoDB for State Lock
```bash
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-2
```

#### ECR Repositories
```bash
aws ecr create-repository \
  --repository-name bmo-learning/ai-service \
  --region us-east-2

aws ecr create-repository \
  --repository-name bmo-learning/rails-api \
  --region us-east-2
```

---

## Phase 1: Infrastructure Deployment (Terraform)

```bash
cd infrastructure/terraform/environments/prod

# Initialize Terraform backend
terraform init \
  -backend-config="bucket=bmo-learning-terraform-state" \
  -backend-config="key=prod/terraform.tfstate" \
  -backend-config="region=us-east-2" \
  -backend-config="encrypt=true" \
  -backend-config="dynamodb_table=terraform-state-lock"

# Plan infrastructure
terraform plan -out=tfplan

# Apply infrastructure
terraform apply tfplan

# Save outputs
terraform output -json > outputs.json
```

---

## Phase 2: Database & Cache Setup

### RDS PostgreSQL
```bash
aws rds create-db-instance \
  --db-instance-identifier bmo-learning-prod-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 16.1 \
  --master-username postgres \
  --master-user-password "secure-password-here" \
  --allocated-storage 100 \
  --multi-az \
  --backup-retention-period 30 \
  --region us-east-2

# Enable pgvector
psql -h DB_ENDPOINT -U postgres -d bmo_learning_prod \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### ElastiCache Redis
```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id bmo-learning-prod-redis \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --engine-version 7.0 \
  --num-cache-nodes 1 \
  --region us-east-2
```

---

## Phase 3: Docker Image Build & Push

```bash
# Login to ECR
aws ecr get-login-password --region us-east-2 | \
  docker login --username AWS --password-stdin \
  ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com

# Build and push AI service
cd app/ai_service
docker build -t bmo-learning/ai-service:latest .
docker tag bmo-learning/ai-service:latest \
  ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/ai-service:latest
docker push ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/ai-service:latest

# Build and push Rails API
cd ../rails_api
docker build -t bmo-learning/rails-api:latest .
docker tag bmo-learning/rails-api:latest \
  ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/rails-api:latest
docker push ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/bmo-learning/rails-api:latest
```

---

## Phase 4: ECS Task Definitions & Services

```bash
# Create task definitions and services via AWS Console or CLI
# See AWS-specific documentation for detailed task definition JSON

aws ecs create-service \
  --cluster bmo-learning-prod \
  --service-name ai-service \
  --task-definition bmo-learning-ai-service:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --region us-east-2

aws ecs create-service \
  --cluster bmo-learning-prod \
  --service-name rails-api \
  --task-definition bmo-learning-rails-api:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --region us-east-2
```

---

## Phase 5: Auto-Scaling

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/bmo-learning-prod/ai-service \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 1 \
  --max-capacity 10 \
  --region us-east-2
```

---

## Cost Estimation (900 learners)

| Service | Cost/Month |
|---------|-----------|
| ECS Fargate (CPU + Memory) | 55 |
| RDS PostgreSQL | 200 |
| ElastiCache Redis | 20 |
| ALB + Networking | 70 |
| Infrastructure Subtotal | 345 |
| | |
| OpenAI LLM (GPT-4) | 300-500 |
| OpenAI Embeddings | 100 |
| Moderation API | 50 |
| LLM Subtotal | 450-650 |
| | |
| TOTAL | 795-995 |

---

## Troubleshooting

Check logs:
```bash
aws logs tail /ecs/bmo-learning-prod --follow
```

Check service status:
```bash
aws ecs describe-services \
  --cluster bmo-learning-prod \
  --services ai-service rails-api \
  --region us-east-2
```

---

**Ready to deploy to AWS us-east-2!**
