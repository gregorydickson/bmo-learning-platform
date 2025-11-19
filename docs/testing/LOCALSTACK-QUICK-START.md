# LocalStack Quick Start Guide

BMO Learning Platform now includes LocalStack integration for testing AWS services locally without incurring AWS costs.

## What is LocalStack?

LocalStack is a fully functional local AWS cloud stack that runs on your machine. It emulates AWS services like S3, Secrets Manager, Lambda, and more.

**Benefits:**
- 🆓 **Zero AWS costs** for testing
- ⚡ **Faster tests** - no network latency to AWS
- 🔒 **Complete offline development** capability
- 🎯 **Production parity** - test with real AWS SDKs
- 🧪 **Test isolation** - clean state for every test

## Quick Start (3 Steps)

### 1. Start LocalStack with Docker Compose

```bash
# Copy LocalStack environment config
cp .env.localstack .env

# Start all services including LocalStack
docker-compose -f docker-compose.yml -f docker-compose.localstack.yml up -d

# Verify LocalStack is running
curl http://localhost:4566/_localstack/health
```

**Expected output:**
```json
{
  "services": {
    "s3": "running",
    "secretsmanager": "running"
  }
}
```

### 2. Run Integration Tests

```bash
cd app/ai_service

# Run ONLY integration tests (requires LocalStack)
docker-compose exec ai_service uv run pytest -m integration -v

# Run ONLY unit tests (no LocalStack needed)
docker-compose exec ai_service uv run pytest -m "not integration" -v

# Run ALL tests
docker-compose exec ai_service uv run pytest -v
```

### 3. Interact with LocalStack S3

```bash
# Install awslocal CLI (optional but recommended)
pip install awscli-local

# List S3 buckets
awslocal s3 ls

# Upload a test document
echo "Test content" > test.txt
awslocal s3 cp test.txt s3://bmo-learning-test-documents/test.txt

# List files in bucket
awslocal s3 ls s3://bmo-learning-test-documents/

# Download file
awslocal s3 cp s3://bmo-learning-test-documents/test.txt downloaded.txt
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   Docker Compose                         │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌────────────┐      ┌────────────┐                     │
│  │ AI Service │─────▶│ LocalStack │ (port 4566)         │
│  │  (Python)  │      │    - S3    │                     │
│  └────────────┘      │  - Secrets │                     │
│                      │    Manager │                      │
│  ┌────────────┐      └────────────┘                     │
│  │ Rails API  │              │                           │
│  │            │──────────────┘                           │
│  └────────────┘                                          │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## Test Types

### Unit Tests (Fast, No LocalStack)
- **Run:** `pytest -m "not integration"`
- **Speed:** < 30 seconds
- **Dependencies:** None (all mocked)
- **Coverage:** 80%+ of business logic
- **Use:** Everyday development, CI for all PRs

### Integration Tests (Slower, Requires LocalStack)
- **Run:** `pytest -m integration`
- **Speed:** < 2 minutes
- **Dependencies:** LocalStack running
- **Coverage:** Real AWS SDK behavior, S3 operations
- **Use:** Before merging, pre-deployment validation

## Environment Configuration

### Development (Local with LocalStack)
```bash
# .env or .env.localstack
AWS_ENDPOINT_URL=http://localhost:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_REGION=us-east-2
USE_LOCALSTACK=true
S3_DOCUMENTS_BUCKET=bmo-learning-test-documents
S3_BACKUPS_BUCKET=bmo-learning-test-backups
```

### Production (Real AWS)
```bash
# .env.production (DO NOT commit)
AWS_ACCESS_KEY_ID=<real-aws-key>
AWS_SECRET_ACCESS_KEY=<real-aws-secret>
AWS_REGION=us-east-2
# AWS_ENDPOINT_URL not set (uses real AWS)
USE_LOCALSTACK=false
S3_DOCUMENTS_BUCKET=bmo-learning-prod-documents
S3_BACKUPS_BUCKET=bmo-learning-prod-backups
```

## Using S3Client in Code

```python
from app.storage.s3_client import S3Client

# Initialize (auto-configures from environment)
client = S3Client()

# Upload a document
result = client.upload_file(
    file_path="/path/to/lesson.pdf",
    bucket="bmo-learning-test-documents",
    key="uploads/python-lesson.pdf",
    metadata={'learner_id': '123', 'topic': 'python'}
)

print(f"Uploaded: {result['etag']}")

# Download a document
result = client.download_file(
    bucket="bmo-learning-test-documents",
    key="uploads/python-lesson.pdf",
    file_path="/tmp/downloaded.pdf"
)

print(f"Downloaded: {result['size_bytes']} bytes")

# List documents
result = client.list_files(
    bucket="bmo-learning-test-documents",
    prefix="uploads/"
)

for file in result['files']:
    print(f"  {file['key']} - {file['size']} bytes")

# Generate shareable URL (valid for 1 hour)
result = client.get_file_url(
    bucket="bmo-learning-test-documents",
    key="uploads/python-lesson.pdf",
    expiration=3600
)

print(f"Share this URL: {result['url']}")
```

## Writing Integration Tests

```python
# tests/test_my_feature.py
import pytest

@pytest.mark.integration
def test_document_upload_to_s3(s3_client, s3_test_bucket):
    """Test uploading a document to S3 via LocalStack."""
    # s3_client: Configured S3Client instance
    # s3_test_bucket: Unique bucket created for this test

    result = s3_client.upload_file(
        file_path="/tmp/test.pdf",
        bucket=s3_test_bucket,
        key="docs/test.pdf"
    )

    assert result['success'] is True
    assert s3_client.file_exists(s3_test_bucket, "docs/test.pdf")

# Bucket automatically cleaned up after test!
```

## Troubleshooting

### LocalStack Not Starting
```bash
# Check logs
docker-compose -f docker-compose.localstack.yml logs localstack

# Common issue: Port 4566 already in use
lsof -i :4566
kill -9 <PID>

# Restart
docker-compose -f docker-compose.yml -f docker-compose.localstack.yml restart localstack
```

### Tests Skipping (LocalStack not detected)
```bash
# Verify LocalStack is accessible
curl http://localhost:4566/_localstack/health

# Check environment variables in container
docker-compose exec ai_service env | grep AWS
```

### S3 Buckets Not Created
```bash
# Check if init script ran
docker-compose -f docker-compose.localstack.yml logs localstack | grep "Initialization Complete"

# Manually run init script
docker-compose exec localstack bash /etc/localstack/init/ready.d/init.sh

# List buckets
awslocal s3 ls
```

### Integration Tests Failing
```bash
# Run with verbose output
docker-compose exec ai_service uv run pytest -m integration -v -s

# Check specific test
docker-compose exec ai_service uv run pytest tests/test_s3_integration.py::test_upload_file_success -v -s
```

## CI/CD Integration

### GitHub Actions
```yaml
# .github/workflows/integration-tests.yml
name: Integration Tests

on: [pull_request, push]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      localstack:
        image: localstack/localstack:latest
        env:
          SERVICES: s3,secretsmanager
        ports:
          - 4566:4566

    steps:
      - uses: actions/checkout@v3

      - name: Wait for LocalStack
        run: |
          timeout 60 bash -c 'until curl -s http://localhost:4566/_localstack/health; do sleep 2; done'

      - name: Run Integration Tests
        run: |
          cd app/ai_service
          uv run pytest -m integration -v
```

## LocalStack Pro Features (Optional)

Current setup uses **Community Edition** (free). Upgrade to **Pro** for:
- ✅ RDS (PostgreSQL testing without Docker)
- ✅ ElastiCache (Redis cluster testing)
- ✅ CloudWatch Logs (log aggregation testing)
- ✅ SES (email delivery testing)
- ✅ Full IAM policy simulation

**Pricing:** $49/month for individuals, $299/month for teams

## Next Steps

1. **Phase 3:** Document Processor S3 Integration
   - Ingest documents directly from S3
   - Process PDFs uploaded to S3 bucket
   - Backup Chroma vector store to S3

2. **Phase 4:** Secrets Manager Integration
   - Load OpenAI API key from Secrets Manager
   - Test secret rotation
   - Migrate all credentials to Secrets Manager

3. **Phase 5:** Rails S3 Service
   - Add S3 upload endpoint to Rails API
   - Integrate with Sidekiq for async processing
   - RSpec tests with LocalStack

4. **Phase 6:** CI/CD Optimization
   - Parallel test execution
   - Separate unit/integration test jobs
   - Cache Docker images for faster builds

## Resources

- [LocalStack Docs](https://docs.localstack.cloud/)
- [boto3 S3 Reference](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html)
- [AWS CLI Local Tool](https://github.com/localstack/awscli-local)
- [LocalStack GitHub](https://github.com/localstack/localstack)

## Cost Savings Calculator

**Without LocalStack:**
- Test environment AWS costs: $150-200/month
- OpenAI API calls in tests: $50-100/month
- Total: **~$250/month**

**With LocalStack:**
- AWS costs: **$0**
- OpenAI API calls (still needed): $50-100/month
- LocalStack Community: **$0**
- Total: **~$75/month** (70% savings)

---

**Last Updated:** 2025-11-18
**LocalStack Version:** latest
**Python SDK:** boto3 >= 1.34.0
