#!/bin/bash
# Phase 5 Verification Script
# Verifies all Rails S3 integration files are in place

set -e

echo "============================================"
echo "Phase 5: Rails S3 Integration Verification"
echo "============================================"
echo ""

ERRORS=0

# Check production files
echo "📦 Checking Production Files..."
echo ""

FILES=(
  "app/rails_api/app/services/s3_service.rb"
  "app/rails_api/app/controllers/api/v1/documents_controller.rb"
  "app/rails_api/app/jobs/document_processing_job.rb"
  "app/rails_api/app/models/document.rb"
  "app/rails_api/db/migrate/20251118000001_create_documents.rb"
)

for file in "${FILES[@]}"; do
  if [ -f "$file" ]; then
    lines=$(wc -l < "$file")
    echo "✅ $file ($lines lines)"
  else
    echo "❌ MISSING: $file"
    ((ERRORS++))
  fi
done

echo ""
echo "📝 Checking Test Files..."
echo ""

TEST_FILES=(
  "app/rails_api/spec/services/s3_service_spec.rb"
  "app/rails_api/spec/jobs/document_processing_job_spec.rb"
  "app/rails_api/spec/requests/api/v1/documents_spec.rb"
  "app/rails_api/spec/models/document_spec.rb"
)

for file in "${TEST_FILES[@]}"; do
  if [ -f "$file" ]; then
    lines=$(wc -l < "$file")
    tests=$(grep -c "it \|context \|describe " "$file" || true)
    echo "✅ $file ($lines lines, ~$tests tests)"
  else
    echo "❌ MISSING: $file"
    ((ERRORS++))
  fi
done

echo ""
echo "⚙️  Checking Configuration..."
echo ""

# Check routes
if grep -q "resources :documents" app/rails_api/config/routes.rb; then
  echo "✅ Documents routes configured"
else
  echo "❌ Documents routes NOT configured"
  ((ERRORS++))
fi

# Check Gemfile
if grep -q "kaminari" app/rails_api/Gemfile; then
  echo "✅ Kaminari gem added"
else
  echo "❌ Kaminari gem NOT added"
  ((ERRORS++))
fi

if grep -q "aws-sdk-s3" app/rails_api/Gemfile; then
  echo "✅ AWS SDK S3 gem present"
else
  echo "❌ AWS SDK S3 gem NOT present"
  ((ERRORS++))
fi

echo ""
echo "📊 Code Metrics..."
echo ""

# Count total lines
TOTAL_PROD=0
for file in "${FILES[@]}"; do
  if [ -f "$file" ]; then
    lines=$(wc -l < "$file")
    TOTAL_PROD=$((TOTAL_PROD + lines))
  fi
done

TOTAL_TEST=0
for file in "${TEST_FILES[@]}"; do
  if [ -f "$file" ]; then
    lines=$(wc -l < "$file")
    TOTAL_TEST=$((TOTAL_TEST + lines))
  fi
done

echo "Production code: $TOTAL_PROD lines"
echo "Test code: $TOTAL_TEST lines"
echo "Test ratio: $(echo "scale=2; $TOTAL_TEST / $TOTAL_PROD" | bc)x"

echo ""
echo "🔍 Code Complexity Check..."
echo ""

# Check S3Service methods
if [ -f "app/rails_api/app/services/s3_service.rb" ]; then
  methods=$(grep -c "def " app/rails_api/app/services/s3_service.rb || true)
  echo "S3Service methods: $methods"
fi

# Check DocumentsController actions
if [ -f "app/rails_api/app/controllers/api/v1/documents_controller.rb" ]; then
  actions=$(grep -c "def " app/rails_api/app/controllers/api/v1/documents_controller.rb || true)
  echo "DocumentsController actions: $actions"
fi

# Check Document model methods
if [ -f "app/rails_api/app/models/document.rb" ]; then
  methods=$(grep -c "def " app/rails_api/app/models/document.rb || true)
  scopes=$(grep -c "scope " app/rails_api/app/models/document.rb || true)
  echo "Document model methods: $methods, scopes: $scopes"
fi

echo ""
echo "============================================"
echo "Verification Summary"
echo "============================================"
echo ""

if [ $ERRORS -eq 0 ]; then
  echo "✅ All Phase 5 files verified successfully!"
  echo ""
  echo "Next Steps:"
  echo "1. Start Docker services: docker-compose -f docker-compose.yml -f docker-compose.localstack.yml up -d"
  echo "2. Run migrations: docker-compose exec rails_api bundle exec rails db:migrate"
  echo "3. Run tests: docker-compose exec rails_api bundle exec rspec"
  echo ""
  exit 0
else
  echo "❌ Verification failed with $ERRORS errors"
  echo ""
  exit 1
fi
