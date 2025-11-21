# Terraform Updates for Anthropic Claude Integration

This document outlines the required Terraform changes to support the Anthropic Claude Haiku model in production.

## Files to Update

### 1. Secrets Manager Module
**File**: `infrastructure/terraform/modules/secrets/main.tf`

Add after the existing `openai_api_key` secret:

```hcl
# Anthropic API Key Secret
resource "aws_secretsmanager_secret" "anthropic_api_key" {
  name        = "bmo-learning/${var.environment}/anthropic-api-key"
  description = "Anthropic API key for Claude models"
  
  recovery_window_in_days = 7
  
  tags = {
    Name        = "bmo-learning-${var.environment}-anthropic-api-key"
    Environment = var.environment
    Service     = "ai-service"
  }
}

resource "aws_secretsmanager_secret_version" "anthropic_api_key" {
  secret_id     = aws_secretsmanager_secret.anthropic_api_key.id
  secret_string = var.anthropic_api_key
}

output "anthropic_api_key_arn" {
  description = "ARN of Anthropic API key secret"
  value       = aws_secretsmanager_secret.anthropic_api_key.arn
}
```

Add variable:

```hcl
variable "anthropic_api_key" {
  description = "Anthropic API key (will be set via AWS Secrets Manager after creation)"
  type        = string
  sensitive   = true
  default     = "PLACEHOLDER_SET_AFTER_CREATION"
}
```

### 2. ECS Services Module
**File**: `infrastructure/terraform/modules/ecs_services/main.tf`

**Update Lines 184-205** (AI Service environment variables):

```hcl
environment = [
  {
    name  = "PYTHON_ENV"
    value = "production"
  },
  {
    name  = "LOG_LEVEL"
    value = "INFO"
  },
  {
    name  = "AWS_REGION"
    value = "us-east-2"
  },
  {
    name  = "ANTHROPIC_MODEL"
    value = "claude-haiku-4-5-20251001"
  },
  {
    name  = "OPENAI_EMBEDDING_MODEL"
    value = "text-embedding-3-small"
  },
  {
    name  = "AI_SERVICE_API_KEY"
    value = var.ai_service_api_key
  }
]
```

**Update Lines 207-220** (AI Service secrets):

```hcl
secrets = [
  {
    name      = "ANTHROPIC_API_KEY"
    valueFrom = var.secret_arns.anthropic_api_key
  },
  {
    name      = "OPENAI_API_KEY"
    valueFrom = var.secret_arns.openai_api_key
  },
  {
    name      = "DATABASE_URL"
    valueFrom = var.secret_arns.database_url
  },
  {
    name      = "REDIS_URL"
    valueFrom = var.secret_arns.redis_url
  }
]
```

**Update Lines 71-82** (secret_arns variable):

```hcl
variable "secret_arns" {
  description = "Map of secret ARNs"
  type = object({
    anthropic_api_key     = string
    openai_api_key        = string
    database_url          = string
    redis_url             = string
    rails_secret_key_base = string
    twilio_account_sid    = string
    twilio_auth_token     = string
    slack_bot_token       = string
  })
}
```

### 3. Main Production Configuration
**File**: `infrastructure/terraform/environments/prod/main.tf`

**Update Lines 258-266** (secret_arns mapping):

```hcl
secret_arns = {
  anthropic_api_key     = module.secrets.anthropic_api_key_arn
  openai_api_key        = module.secrets.openai_api_key_arn
  database_url          = module.secrets.database_url_arn
  redis_url             = module.secrets.redis_url_arn
  rails_secret_key_base = module.secrets.rails_secret_key_base_arn
  twilio_account_sid    = module.secrets.twilio_account_sid_arn
  twilio_auth_token     = module.secrets.twilio_auth_token_arn
  slack_bot_token       = module.secrets.slack_bot_token_arn
}
```

## Deployment Steps

### Step 1: Apply Terraform Changes

```bash
cd infrastructure/terraform/environments/prod

# Initialize (if not already done)
terraform init

# Review changes
terraform plan

# Apply changes
terraform apply
```

### Step 2: Set Anthropic API Key

After Terraform creates the secret, set the actual value:

```bash
aws secretsmanager put-secret-value \
  --secret-id bmo-learning/prod/anthropic-api-key \
  --secret-string "sk-ant-api03-YOUR_ACTUAL_KEY_HERE" \
  --region us-east-2
```

### Step 3: Verify Secret

```bash
# Verify the secret exists
aws secretsmanager describe-secret \
  --secret-id bmo-learning/prod/anthropic-api-key \
  --region us-east-2

# Test retrieval (will show the value)
aws secretsmanager get-secret-value \
  --secret-id bmo-learning/prod/anthropic-api-key \
  --region us-east-2 \
  --query SecretString \
  --output text
```

### Step 4: Update ECS Services

The ECS services will automatically pick up the new environment variables and secrets on the next deployment or task restart.

To force an immediate update:

```bash
# Update AI service
aws ecs update-service \
  --cluster bmo-learning-prod \
  --service bmo-learning-prod-ai-service \
  --force-new-deployment \
  --region us-east-2
```

### Step 5: Verify Deployment

```bash
# Check service status
aws ecs describe-services \
  --cluster bmo-learning-prod \
  --services bmo-learning-prod-ai-service \
  --region us-east-2 \
  --query 'services[0].deployments'

# Check task logs
aws logs tail /ecs/bmo-learning-prod/ai-service \
  --follow \
  --region us-east-2
```

## Validation

After deployment, verify the AI service is using Claude:

```bash
# Test lesson generation endpoint
curl -X POST https://<alb-dns-name>/api/v1/generate-lesson \
  -H "X-API-Key: <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "APR",
    "learner_id": "test_user"
  }'

# Test agent endpoint
curl -X POST https://<alb-dns-name>/api/v1/agent/chat \
  -H "X-API-Key: <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "learner_id": "test_user",
    "message": "Explain APR to me"
  }'
```

Check the CloudWatch logs to confirm Claude model is being used:

```bash
aws logs filter-log-events \
  --log-group-name /ecs/bmo-learning-prod/ai-service \
  --filter-pattern "claude-haiku" \
  --region us-east-2
```

## Rollback Plan

If issues occur, rollback by:

1. **Revert Terraform changes**:
   ```bash
   git revert <commit-hash>
   terraform apply
   ```

2. **Or manually update environment variables**:
   ```bash
   # Update task definition to use old environment variables
   # Force new deployment
   aws ecs update-service \
     --cluster bmo-learning-prod \
     --service bmo-learning-prod-ai-service \
     --task-definition <previous-task-definition-arn> \
     --region us-east-2
   ```

## Cost Impact

**Anthropic Claude Haiku Pricing**:
- Input: $0.25 per 1M tokens
- Output: $1.25 per 1M tokens

**Comparison to GPT-4 Turbo**:
- Claude Haiku is ~10x cheaper than GPT-4 Turbo
- Expected monthly savings: ~$200-500 depending on usage

**OpenAI Embeddings** (still required):
- text-embedding-3-small: $0.02 per 1M tokens
- Minimal cost impact (~$5-10/month)

## Notes

- Both Anthropic and OpenAI API keys are required
- Anthropic is used for lesson generation and agent reasoning
- OpenAI is used for embeddings (Anthropic doesn't provide embedding models)
- The application gracefully handles missing OpenAI moderation if only Anthropic key is provided
