#!/bin/bash
# LocalStack Resource Verification Script
# Verifies S3 buckets and Secrets Manager secrets are created

set -e

LOCALSTACK_URL="${AWS_ENDPOINT_URL:-http://localhost:4566}"
AWS_REGION="${AWS_REGION:-us-east-2}"

echo "============================================"
echo "LocalStack Resource Verification"
echo "============================================"
echo "Endpoint: $LOCALSTACK_URL"
echo "Region: $AWS_REGION"
echo ""

ERRORS=0

# Check if awslocal is available
if ! command -v awslocal &> /dev/null; then
  echo "⚠️  awslocal not found. Install with: pip install awscli-local"
  echo "   Falling back to aws cli with --endpoint-url"
  AWS_CMD="aws --endpoint-url=$LOCALSTACK_URL"
else
  AWS_CMD="awslocal"
fi

# Function to check S3 bucket
check_bucket() {
  local bucket=$1
  echo -n "Checking S3 bucket: $bucket... "

  if $AWS_CMD s3 ls "s3://$bucket" --region $AWS_REGION > /dev/null 2>&1; then
    echo "✅ exists"
    return 0
  else
    echo "❌ NOT FOUND"
    ((ERRORS++))
    return 1
  fi
}

# Function to check secret
check_secret() {
  local secret_name=$1
  echo -n "Checking secret: $secret_name... "

  if $AWS_CMD secretsmanager describe-secret --secret-id "$secret_name" --region $AWS_REGION > /dev/null 2>&1; then
    echo "✅ exists"
    return 0
  else
    echo "❌ NOT FOUND"
    ((ERRORS++))
    return 1
  fi
}

echo "📦 Checking S3 Buckets..."
echo ""

BUCKETS=(
  "bmo-learning-test-documents"
  "bmo-learning-test-backups"
)

for bucket in "${BUCKETS[@]}"; do
  check_bucket "$bucket"
done

echo ""
echo "🔐 Checking Secrets Manager Secrets..."
echo ""

SECRETS=(
  "bmo-learning/test/openai-api-key"
  "bmo-learning/test/database-credentials"
)

for secret in "${SECRETS[@]}"; do
  check_secret "$secret"
done

echo ""
echo "============================================"
echo "Verification Summary"
echo "============================================"
echo ""

if [ $ERRORS -eq 0 ]; then
  echo "✅ All resources verified successfully!"
  echo ""
  echo "Detailed Information:"
  echo ""

  echo "📦 S3 Buckets:"
  $AWS_CMD s3 ls --region $AWS_REGION | grep bmo-learning || echo "  (none found)"

  echo ""
  echo "🔐 Secrets:"
  $AWS_CMD secretsmanager list-secrets --region $AWS_REGION --query 'SecretList[?contains(Name, `bmo-learning`)].Name' --output table 2>/dev/null || echo "  (none found)"

  echo ""
  echo "📄 Sample bucket contents:"
  for bucket in "${BUCKETS[@]}"; do
    echo ""
    echo "  $bucket:"
    $AWS_CMD s3 ls "s3://$bucket" --recursive --region $AWS_REGION 2>/dev/null | head -5 || echo "    (empty)"
  done

  echo ""
  exit 0
else
  echo "❌ Verification failed with $ERRORS errors"
  echo ""
  echo "Run LocalStack initialization script:"
  echo "  ./scripts/localstack-init.sh"
  echo ""
  exit 1
fi
