# Architectural Review Fixes

## Summary
This document outlines the fixes applied following the architectural review of the BMO Learning Platform.

## 1. Security: AI Service Authentication
**Issue**: The AI Service endpoints were unauthenticated, posing a security risk.
**Fix**:
- Implemented API Key authentication using `X-API-Key` header.
- Added `get_api_key` dependency to FastAPI service.
- Enforced authentication on all `/api/v1` routes.
- Updated Rails `AiServiceClient` to send the API key in requests.
- Added `AI_SERVICE_API_KEY` to configuration and environment variables.

## 2. Service Communication
**Issue**: The Rails API was configured to contact the AI Service via `localhost` in production, which would fail in a containerized ECS environment.
**Fix**:
- Updated Terraform `ecs_services` module to accept `ai_service_url` and `ai_service_api_key`.
- Updated `prod` environment configuration to pass the Application Load Balancer (ALB) DNS name as the `AI_SERVICE_URL`.
- This ensures Rails calls the AI Service via the internal ALB, which correctly routes requests based on path patterns.

## 3. Database Migrations
**Issue**: The Rails Docker image lacked a mechanism to run database migrations in the production environment.
**Fix**:
- Created `app/rails_api/bin/docker-entrypoint` script.
- Configured the script to run `bin/rails db:prepare` (which handles creation and migration) before starting the server.
- Updated `app/rails_api/Dockerfile` to use this entrypoint.

## 4. Configuration
**Updates**:
- Added `AI_SERVICE_API_KEY` to `.env.example`.
- Updated Terraform variables to support the new configuration.

## Verification
- **Local Development**: Uses default `dev_key` and `localhost` URLs.
- **Production**: Uses secure API keys (managed via Secrets Manager/Terraform) and ALB routing.
