#!/bin/bash
# LocalStack Health Check Script
# Verifies LocalStack is running and services are ready

set -e

LOCALSTACK_URL="${LOCALSTACK_URL:-http://localhost:4566}"
MAX_RETRIES="${MAX_RETRIES:-30}"
RETRY_INTERVAL="${RETRY_INTERVAL:-2}"

echo "============================================"
echo "LocalStack Health Check"
echo "============================================"
echo "URL: $LOCALSTACK_URL"
echo "Max retries: $MAX_RETRIES"
echo "Retry interval: ${RETRY_INTERVAL}s"
echo ""

# Function to check LocalStack health
check_health() {
  curl -sf "$LOCALSTACK_URL/_localstack/health" > /dev/null 2>&1
  return $?
}

# Function to check specific service
check_service() {
  local service=$1
  local health_data=$(curl -sf "$LOCALSTACK_URL/_localstack/health")

  if [ -z "$health_data" ]; then
    return 1
  fi

  # Check if service is in the response and running
  echo "$health_data" | grep -q "\"$service\"" && \
  echo "$health_data" | grep -q "\"$service\"[^}]*\"running\"" || \
  echo "$health_data" | grep -q "\"$service\"[^}]*\"available\""
  return $?
}

# Wait for LocalStack to be ready
echo "⏳ Waiting for LocalStack to start..."
retry_count=0

while ! check_health; do
  retry_count=$((retry_count + 1))

  if [ $retry_count -ge $MAX_RETRIES ]; then
    echo "❌ LocalStack failed to start after $MAX_RETRIES retries"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check if LocalStack container is running: docker ps | grep localstack"
    echo "2. Check LocalStack logs: docker logs <container-id>"
    echo "3. Try restarting: docker-compose restart localstack"
    exit 1
  fi

  echo "   Attempt $retry_count/$MAX_RETRIES - waiting ${RETRY_INTERVAL}s..."
  sleep $RETRY_INTERVAL
done

echo "✅ LocalStack is running!"
echo ""

# Get health status
echo "📊 Service Status:"
echo ""

health_json=$(curl -sf "$LOCALSTACK_URL/_localstack/health")

if [ $? -eq 0 ]; then
  # Check required services
  services=("s3" "secretsmanager")
  all_healthy=true

  for service in "${services[@]}"; do
    if check_service "$service"; then
      echo "✅ $service: ready"
    else
      echo "❌ $service: not ready"
      all_healthy=false
    fi
  done

  echo ""

  # Show full health response (pretty-printed if jq available)
  if command -v jq &> /dev/null; then
    echo "Full Health Status:"
    echo "$health_json" | jq '.'
  else
    echo "Raw Health Status:"
    echo "$health_json"
  fi

  echo ""

  if [ "$all_healthy" = true ]; then
    echo "✅ All required services are healthy!"
    exit 0
  else
    echo "⚠️  Some services are not ready. Tests may fail."
    exit 1
  fi
else
  echo "❌ Failed to retrieve health status"
  exit 1
fi
