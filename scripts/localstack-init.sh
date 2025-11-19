#!/bin/bash

# LocalStack Initialization Script
# This script runs when LocalStack becomes "ready"
# Creates S3 buckets, Secrets Manager secrets, and IAM policies

set -e

echo "=================================================="
echo "LocalStack Initialization Script Starting..."
echo "=================================================="

# Configuration
REGION="us-east-2"
DOCUMENTS_BUCKET="bmo-learning-test-documents"
BACKUPS_BUCKET="bmo-learning-test-backups"

# Wait for LocalStack to be fully ready
echo "Waiting for LocalStack services..."
sleep 5

# ===================================================
# S3 Bucket Creation
# ===================================================
echo ""
echo "Creating S3 Buckets..."

# Create documents bucket
if awslocal s3 mb "s3://${DOCUMENTS_BUCKET}" --region "${REGION}" 2>/dev/null; then
    echo "✓ Created bucket: ${DOCUMENTS_BUCKET}"
else
    echo "⚠ Bucket already exists: ${DOCUMENTS_BUCKET}"
fi

# Create backups bucket
if awslocal s3 mb "s3://${BACKUPS_BUCKET}" --region "${REGION}" 2>/dev/null; then
    echo "✓ Created bucket: ${BACKUPS_BUCKET}"
else
    echo "⚠ Bucket already exists: ${BACKUPS_BUCKET}"
fi

# Enable versioning on documents bucket
awslocal s3api put-bucket-versioning \
    --bucket "${DOCUMENTS_BUCKET}" \
    --versioning-configuration Status=Enabled \
    --region "${REGION}"
echo "✓ Enabled versioning on ${DOCUMENTS_BUCKET}"

# Enable versioning on backups bucket
awslocal s3api put-bucket-versioning \
    --bucket "${BACKUPS_BUCKET}" \
    --versioning-configuration Status=Enabled \
    --region "${REGION}"
echo "✓ Enabled versioning on ${BACKUPS_BUCKET}"

# Add lifecycle policy to backups bucket (simulating production)
# COMMENTED OUT: LocalStack lifecycle configuration causing MalformedXML errors
# This is non-critical for local testing - lifecycle policies are production-only simulation
# LIFECYCLE_POLICY='{
#   "Rules": [
#     {
#       "ID": "TransitionToGlacier",
#       "Status": "Enabled",
#       "Prefix": "",
#       "Transitions": [
#         {
#           "Days": 30,
#           "StorageClass": "GLACIER"
#         }
#       ]
#     }
#   ]
# }'
#
# awslocal s3api put-bucket-lifecycle-configuration \
#     --bucket "${BACKUPS_BUCKET}" \
#     --lifecycle-configuration "${LIFECYCLE_POLICY}" \
#     --region "${REGION}"
# echo "✓ Applied lifecycle policy to ${BACKUPS_BUCKET}"
echo "⚠ Skipping lifecycle policy (non-critical for local testing)"

# ===================================================
# Secrets Manager - Create Test Secrets
# ===================================================
echo ""
echo "Creating Secrets Manager Secrets..."

# OpenAI API Key (test value)
SECRET_NAME="bmo-learning/test/openai-api-key"
SECRET_VALUE="sk-test-localstack-fake-key-for-testing-only"

if awslocal secretsmanager create-secret \
    --name "${SECRET_NAME}" \
    --secret-string "${SECRET_VALUE}" \
    --region "${REGION}" 2>/dev/null; then
    echo "✓ Created secret: ${SECRET_NAME}"
else
    echo "⚠ Secret already exists: ${SECRET_NAME}"
    # Update if exists
    awslocal secretsmanager put-secret-value \
        --secret-id "${SECRET_NAME}" \
        --secret-string "${SECRET_VALUE}" \
        --region "${REGION}"
    echo "✓ Updated secret: ${SECRET_NAME}"
fi

# Database credentials (test values)
DB_SECRET_NAME="bmo-learning/test/database-credentials"
DB_SECRET_VALUE='{
  "username": "postgres",
  "password": "postgres",
  "host": "postgres",
  "port": "5432",
  "dbname": "bmo_learning_test"
}'

if awslocal secretsmanager create-secret \
    --name "${DB_SECRET_NAME}" \
    --secret-string "${DB_SECRET_VALUE}" \
    --region "${REGION}" 2>/dev/null; then
    echo "✓ Created secret: ${DB_SECRET_NAME}"
else
    echo "⚠ Secret already exists: ${DB_SECRET_NAME}"
fi

# Redis credentials (test values)
REDIS_SECRET_NAME="bmo-learning/test/redis-credentials"
REDIS_SECRET_VALUE='{
  "host": "redis",
  "port": "6379"
}'

if awslocal secretsmanager create-secret \
    --name "${REDIS_SECRET_NAME}" \
    --secret-string "${REDIS_SECRET_VALUE}" \
    --region "${REGION}" 2>/dev/null; then
    echo "✓ Created secret: ${REDIS_SECRET_NAME}"
else
    echo "⚠ Secret already exists: ${REDIS_SECRET_NAME}"
fi

# ===================================================
# IAM Policies (Optional - for testing)
# ===================================================
echo ""
echo "Creating IAM Policies..."

# S3 Read/Write Policy
POLICY_NAME="BMOLearningS3Policy"
POLICY_DOCUMENT='{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::bmo-learning-test-documents",
        "arn:aws:s3:::bmo-learning-test-documents/*",
        "arn:aws:s3:::bmo-learning-test-backups",
        "arn:aws:s3:::bmo-learning-test-backups/*"
      ]
    }
  ]
}'

if awslocal iam create-policy \
    --policy-name "${POLICY_NAME}" \
    --policy-document "${POLICY_DOCUMENT}" \
    --region "${REGION}" 2>/dev/null; then
    echo "✓ Created IAM policy: ${POLICY_NAME}"
else
    echo "⚠ IAM policy already exists: ${POLICY_NAME}"
fi

# ===================================================
# Upload Test Documents
# ===================================================
echo ""
echo "Uploading Test Documents..."

# Create temporary test files
TMP_DIR="/tmp/localstack-test-files"
mkdir -p "${TMP_DIR}"

# Create test PDF content
echo "This is a test document for BMO Learning Platform LocalStack testing." > "${TMP_DIR}/test-document.txt"
echo "Sample learning content about Python programming." > "${TMP_DIR}/python-lesson.txt"
echo "Sample learning content about Machine Learning." > "${TMP_DIR}/ml-lesson.txt"

# Upload test files
awslocal s3 cp "${TMP_DIR}/test-document.txt" "s3://${DOCUMENTS_BUCKET}/test/test-document.txt" --region "${REGION}"
echo "✓ Uploaded test-document.txt"

awslocal s3 cp "${TMP_DIR}/python-lesson.txt" "s3://${DOCUMENTS_BUCKET}/lessons/python-lesson.txt" --region "${REGION}"
echo "✓ Uploaded python-lesson.txt"

awslocal s3 cp "${TMP_DIR}/ml-lesson.txt" "s3://${DOCUMENTS_BUCKET}/lessons/ml-lesson.txt" --region "${REGION}"
echo "✓ Uploaded ml-lesson.txt"

# Clean up
rm -rf "${TMP_DIR}"

# ===================================================
# Verification
# ===================================================
echo ""
echo "Verifying LocalStack Setup..."

# List S3 buckets
echo ""
echo "S3 Buckets:"
awslocal s3 ls --region "${REGION}"

# List objects in documents bucket
echo ""
echo "Documents in ${DOCUMENTS_BUCKET}:"
awslocal s3 ls "s3://${DOCUMENTS_BUCKET}/" --recursive --region "${REGION}"

# List secrets
echo ""
echo "Secrets Manager Secrets:"
awslocal secretsmanager list-secrets --region "${REGION}" --query 'SecretList[*].Name' --output text

echo ""
echo "=================================================="
echo "LocalStack Initialization Complete!"
echo "=================================================="
echo ""
echo "Available Services:"
echo "  - S3 Buckets: ${DOCUMENTS_BUCKET}, ${BACKUPS_BUCKET}"
echo "  - Secrets: OpenAI API Key, Database Credentials, Redis Credentials"
echo "  - IAM Policies: ${POLICY_NAME}"
echo ""
echo "Test the setup:"
echo "  awslocal s3 ls"
echo "  awslocal secretsmanager list-secrets"
echo "  curl http://localhost:4566/_localstack/health"
echo ""
