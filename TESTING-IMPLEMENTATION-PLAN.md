# Unit Testing Implementation Plan
**Target Coverage:** 80%+ for both services
**Status:** In Progress
**Start Date:** 2025-11-16

---

## Python AI Service Tests (app/ai_service/tests/)

### Phase 1: Test Infrastructure Setup
- [ ] Create tests directory structure
- [ ] Set up conftest.py with fixtures
- [ ] Create mock data generators
- [ ] Configure pytest settings
- [ ] Add test requirements to pyproject.toml

### Phase 2: Core Business Logic Tests

#### A. Safety Validator Tests (test_safety_validator.py)
- [ ] Test PII detection (SSN, credit cards, emails, phones)
- [ ] Test constitutional AI validation
- [ ] Test content moderation API integration (mocked)
- [ ] Test content sanitization
- [ ] Test edge cases (empty content, special characters)
- [ ] Test validation result structure
**Priority:** CRITICAL (security-related)

#### B. Lesson Generator Tests (test_lesson_generator.py)
- [ ] Test basic lesson generation
- [ ] Test lesson generation with RAG context
- [ ] Test lesson generation without RAG (fallback)
- [ ] Test personalization based on learner context
- [ ] Test difficulty level handling
- [ ] Test output structure validation
- [ ] Test OpenAI API error handling (mocked)
- [ ] Test prompt template rendering
**Priority:** CRITICAL (core functionality)

#### C. Vector Store Tests (test_vector_store.py)
- [ ] Test vector store creation
- [ ] Test vector store loading
- [ ] Test document embedding
- [ ] Test similarity search
- [ ] Test persistence/reload
- [ ] Test empty vector store handling
- [ ] Test Chroma client initialization
**Priority:** HIGH

#### D. Document Processor Tests (test_document_processor.py)
- [ ] Test PDF document processing
- [ ] Test text document processing
- [ ] Test directory processing
- [ ] Test text chunking
- [ ] Test metadata extraction
- [ ] Test invalid file handling
- [ ] Test empty document handling
**Priority:** MEDIUM

### Phase 3: API & Integration Tests

#### E. API Routes Tests (test_api_routes.py)
- [ ] Test /status endpoint
- [ ] Test /generate-lesson endpoint (success)
- [ ] Test /generate-lesson endpoint (validation errors)
- [ ] Test /generate-lesson endpoint (safety failures)
- [ ] Test /validate-safety endpoint
- [ ] Test /ingest-documents endpoint
- [ ] Test error responses (4xx, 5xx)
- [ ] Test request/response schemas
**Priority:** HIGH

#### F. Caching Tests (test_caching.py)
- [ ] Test cache key generation
- [ ] Test cache hit
- [ ] Test cache miss
- [ ] Test cache expiration
- [ ] Test cache invalidation
- [ ] Test Redis connection handling
**Priority:** HIGH (after implementing caching)

### Phase 4: Utilities & Configuration

#### G. Logging Tests (test_logging.py)
- [ ] Test structured logging configuration
- [ ] Test LLM call logging
- [ ] Test log formatting
**Priority:** LOW

#### H. Settings Tests (test_settings.py)
- [ ] Test environment variable loading
- [ ] Test default values
- [ ] Test required field validation
**Priority:** LOW

---

## Rails API Tests (app/rails_api/spec/)

### Phase 1: Test Infrastructure Setup
- [ ] Create spec directory structure
- [ ] Set up rails_helper.rb and spec_helper.rb
- [ ] Create FactoryBot factories
- [ ] Configure SimpleCov for coverage
- [ ] Add database_cleaner configuration
- [ ] Set up VCR for HTTP mocking

### Phase 2: Model Tests

#### A. Learner Model Tests (spec/models/learner_spec.rb)
- [ ] Test validations (email presence, uniqueness)
- [ ] Test associations (has_many lessons, learning_paths)
- [ ] Test JSONB fields (preferences, metadata)
- [ ] Test scopes (if any)
- [ ] Test callbacks (if any)
**Priority:** HIGH

#### B. Lesson Model Tests (spec/models/lesson_spec.rb)
- [ ] Test validations (topic, content presence)
- [ ] Test associations (belongs_to learner)
- [ ] Test status transitions
- [ ] Test completion tracking
**Priority:** HIGH

#### C. LearningPath Model Tests (spec/models/learning_path_spec.rb)
- [ ] Test validations
- [ ] Test associations
- [ ] Test progress calculation
**Priority:** MEDIUM

#### D. QuizResponse Model Tests (spec/models/quiz_response_spec.rb)
- [ ] Test validations
- [ ] Test associations
- [ ] Test correctness checking
**Priority:** MEDIUM

### Phase 3: Service Object Tests

#### E. AI Service Client Tests (spec/services/ai_service_client_spec.rb)
- [ ] Test successful lesson generation request
- [ ] Test HTTP timeout handling
- [ ] Test connection error handling
- [ ] Test response parsing
- [ ] Test error response handling
- [ ] Test retry logic (if implemented)
**Priority:** CRITICAL

#### F. Lesson Generation Service Tests (spec/services/lesson_generation_service_spec.rb)
- [ ] Test Success() path
- [ ] Test Failure() path
- [ ] Test learner context building
- [ ] Test AI service integration
- [ ] Test lesson persistence
**Priority:** HIGH

#### G. Delivery Services Tests
- [ ] spec/services/slack_delivery_service_spec.rb
- [ ] spec/services/sms_delivery_service_spec.rb
- [ ] spec/services/email_delivery_service_spec.rb
- [ ] Test message formatting
- [ ] Test API error handling
- [ ] Test delivery confirmation
**Priority:** MEDIUM

### Phase 4: Background Job Tests

#### H. Job Tests (spec/jobs/)
- [ ] spec/jobs/lesson_generation_job_spec.rb
- [ ] spec/jobs/lesson_delivery_job_spec.rb
- [ ] Test job enqueuing
- [ ] Test job execution
- [ ] Test error handling
- [ ] Test retry behavior
**Priority:** HIGH

### Phase 5: Controller/Request Tests

#### I. API Request Tests (spec/requests/api/v1/)
- [ ] spec/requests/api/v1/learners_spec.rb
  - [ ] GET /api/v1/learners (index)
  - [ ] GET /api/v1/learners/:id (show)
  - [ ] POST /api/v1/learners (create)
  - [ ] PATCH /api/v1/learners/:id (update)
  - [ ] DELETE /api/v1/learners/:id (destroy)
  - [ ] POST /api/v1/learners/:id/request_lesson
- [ ] spec/requests/api/v1/lessons_spec.rb
- [ ] spec/requests/api/v1/learning_paths_spec.rb
- [ ] Test authentication (if implemented)
- [ ] Test authorization (Pundit policies)
- [ ] Test JSON response structure
**Priority:** HIGH

---

## Test Execution & Validation

### Python AI Service
- [ ] Run `uv run pytest --cov` - verify >80% coverage
- [ ] Run `uv run pytest -v` - all tests pass
- [ ] Fix any failing tests
- [ ] Generate HTML coverage report
- [ ] Review uncovered lines

### Rails API
- [ ] Run `bundle exec rspec` - all tests pass
- [ ] Run `bundle exec rspec --format documentation`
- [ ] Verify >80% coverage in SimpleCov output
- [ ] Fix any failing tests
- [ ] Review uncovered code

### CI/CD Validation
- [ ] Push to branch and verify GitHub Actions pass
- [ ] Fix any CI/CD-specific failures
- [ ] Verify coverage reports upload to Codecov

---

## Success Criteria

✅ **Python AI Service:**
- Minimum 15 test files
- 80%+ line coverage
- 80%+ branch coverage
- All critical paths tested
- All security features tested

✅ **Rails API:**
- Minimum 20 test files
- 80%+ line coverage
- All models have validation tests
- All API endpoints have request tests
- All services have unit tests

---

## Estimated Timeline

- **Python Tests:** 2-3 days
- **Rails Tests:** 2-3 days
- **Total:** 4-6 days

---

## Dependencies to Mock

### Python
- OpenAI API calls
- Chroma vector store (for some tests)
- Redis connections (for cache tests)
- HTTP requests

### Rails
- AI Service HTTP calls (use WebMock)
- Twilio API (use VCR)
- Slack API (use VCR)
- External email services

---

**Next Step:** Begin Phase 1 - Python Test Infrastructure Setup
