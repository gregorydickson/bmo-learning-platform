# Getting Started - BMO Learning Platform

**Goal**: Get from empty directory to working Phase 1 foundation in one session

**Latest Versions**: LangChain 1.0.7 | Rails 7.2.3 | OpenAI 2.8.0 | FastAPI 0.121.2

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] **Docker Desktop** installed and running
  ```bash
  docker --version  # Should show 20.x or newer
  docker-compose --version  # Should show 2.x or newer
  ```

- [ ] **Python 3.11+** installed
  ```bash
  python3 --version  # Should show 3.11.x or newer
  ```

- [ ] **Ruby 3.2+** installed
  ```bash
  ruby --version  # Should show 3.2.x or newer
  ```

- [ ] **uv** (Python package manager) installed
  ```bash
  pip install uv
  ```

- [ ] **OpenAI API Key** obtained
  - Create account at: https://platform.openai.com/
  - Generate API key: https://platform.openai.com/api-keys
  - Set minimum credit ($5 recommended for testing)

- [ ] **Git** configured
  ```bash
  git config --global user.name "Your Name"
  git config --global user.email "your.email@example.com"
  ```

## Recommended Implementation Path

**All documentation has been updated with the latest API versions and fixes integrated.**

### Quick Start (Recommended)

1. **Navigate to project**
   ```bash
   cd /Users/gregorydickson/learning-app
   ```

2. **Read Phase 1 workplan**
   ```bash
   cat docs/workplans/01-foundation-setup.md
   ```
   All fixes have been integrated directly into the workplans.

3. **Set up environment**
   ```bash
   # Create .env file
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

4. **Follow Phase 1 workplan**
   All code examples use the latest stable versions:
   - LangChain 1.0.7
   - Rails 7.2.3
   - OpenAI 2.8.0
   - FastAPI 0.121.2
   - Pydantic 2.12.4

5. **Start services** (after Phase 1 complete)
   ```bash
   docker-compose up
   ```

6. **Verify**
   ```bash
   curl http://localhost:8000/health  # Python AI service
   curl http://localhost:3000/health  # Rails API
   ```

## Option 2: Step-by-Step (Agent-Driven)

**Best for**: Learning implementation, understanding architecture

### Phase 1: Foundation & Setup (Start Here)

**Estimated Time**: 6-8 days
**Goal**: Project scaffold, Docker environment, CI/CD pipeline

#### Day 1-2: Project Structure & Dependencies

1. **Read the workplan**
   ```bash
   cat docs/workplans/01-foundation-setup.md
   ```

2. **Start with Section 1.1: Create Directory Scaffold**
   - Create all directories as specified
   - Initialize git repository
   - Create .gitignore and .env.example

3. **Move to Section 2: Dependency Management**
   - Set up Python dependencies (pyproject.toml)
   - Initialize Rails app
   - Configure bundler

**Agent Instruction**: "Implement Section 1.1 and 2 from Phase 1 workplan. Check off items as you complete them."

#### Day 3-4: Docker Configuration

4. **Implement Section 3: Docker Configuration**
   - Create Dockerfiles for Python and Rails
   - Create docker-compose.yml
   - Test: `docker-compose up` should start all services

**Agent Instruction**: "Implement Section 3 from Phase 1 workplan. Ensure all services start successfully."

#### Day 5: Development Tooling

5. **Implement Section 4: Development Tooling**
   - Pre-commit hooks
   - EditorConfig
   - Development scripts

**Agent Instruction**: "Implement Section 4 from Phase 1 workplan. Test pre-commit hooks."

#### Day 6-7: CI/CD & Documentation

6. **Implement Section 5: CI/CD Pipeline**
   - GitHub Actions workflows
   - Security scanning

7. **Implement Section 6-8: Documentation & Security**
   - Complete README
   - Security configuration
   - Quality gates

**Agent Instruction**: "Implement Sections 5-8 from Phase 1 workplan. Verify all tests pass in CI."

#### Day 8: Phase 1 Review

8. **Validation Checklist**
   - [ ] `docker-compose up` starts all services
   - [ ] Health endpoints return 200
   - [ ] Pre-commit hooks run on commit
   - [ ] CI/CD pipelines pass
   - [ ] All Phase 1 checkboxes marked

**Next**: Proceed to Phase 2 (LangChain AI Service)

### Subsequent Phases

Once Phase 1 is complete, follow this sequence:

1. **Phase 2**: LangChain AI Service (10-14 days)
   - Read: `docs/workplans/02-langchain-service.md`
   - Start with Section 1: Core Infrastructure
   - Agent instruction: "Implement Phase 2, Section 1"

2. **Phase 3**: Rails API Service (10-12 days)
   - Read: `docs/workplans/03-rails-api.md`

3. **Phase 4**: ML Pipeline & Analytics (8-10 days)
   - Read: `docs/workplans/04-ml-analytics.md`

4. **Phase 5**: Infrastructure & Deployment (8-10 days)
   - Read: `docs/workplans/05-infrastructure.md`

5. **Phase 6**: Security & Compliance (6-8 days)
   - Read: `docs/workplans/06-security-compliance.md`

## Agent Workflow Pattern

When working with a coding agent, follow this pattern for each phase:

### Session Start
```
1. Read current phase workplan
2. Check which items are incomplete
3. Pick next unchecked item
4. Implement it
5. Test it
6. Check it off
7. Commit working code
8. Repeat
```

### Example Agent Prompts

**Starting a phase**:
```
"I'm starting Phase 2 of the BMO Learning Platform. Please read
docs/workplans/02-langchain-service.md and implement Section 1.1
(FastAPI Application Bootstrap). Check off items as you complete them."
```

**Continuing a phase**:
```
"Continue Phase 2. Implement the next unchecked section.
Run tests after implementation."
```

**Debugging**:
```
"Section 2.3 (Advanced Retrieval Strategies) is failing tests.
Debug and fix, then mark as complete."
```

## Development Workflow

### Daily Routine

1. **Pull latest changes**
   ```bash
   git pull origin main
   ```

2. **Start services**
   ```bash
   docker-compose up -d
   ```

3. **Check service health**
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:3000/health
   ```

4. **Work on current phase**
   - Read relevant workplan section
   - Implement feature
   - Write tests
   - Run tests locally

5. **Commit progress**
   ```bash
   git add .
   git commit -m "Implement [feature] - Phase X, Section Y.Z"
   git push
   ```

6. **End of day**
   - Update workplan checkboxes
   - Document any blocking issues
   - Shut down services: `docker-compose down`

### Testing Workflow

**Python (AI Service)**:
```bash
cd app/ai_service
uv run pytest --cov --cov-report=html
open htmlcov/index.html  # View coverage report
```

**Rails (API Service)**:
```bash
cd app/rails_api
bundle exec rspec --format documentation
open coverage/index.html  # View coverage report
```

### Debugging Tips

**Service won't start**:
```bash
docker-compose logs -f [service_name]
docker-compose down
docker-compose up --build  # Rebuild images
```

**Database issues**:
```bash
docker-compose down -v  # Remove volumes
docker-compose up  # Fresh start
cd app/rails_api && bundle exec rails db:create db:migrate
```

**Port already in use**:
```bash
lsof -i :8000  # Find process on port 8000
kill -9 [PID]  # Kill process
```

## Common Pitfalls & Solutions

### Issue: OpenAI API rate limits
**Solution**:
- Enable Redis caching (reduces calls by 60%)
- Use tier 1 or higher API account
- Implement exponential backoff

### Issue: Tests failing in CI but passing locally
**Solution**:
- Check environment variables in GitHub Actions
- Ensure test database is properly seeded
- Review service dependencies (db, redis)

### Issue: Vector store not persisting
**Solution**:
- Check Docker volume mounts
- Verify Chroma persist directory exists
- Review docker-compose.yml volume configuration

### Issue: High LLM costs during development
**Solution**:
- Use smaller models for testing (gpt-3.5-turbo)
- Mock LLM responses in unit tests
- Enable aggressive caching
- Limit test data volume

## Resources

### Documentation
- [Master Workplan](workplans/00-MASTER-WORKPLAN.md) - Full project plan
- [Architecture Overview](architecture/overview.md) - System design
- [Phase 1 Workplan](workplans/01-foundation-setup.md) - Start here

### External Resources
- [LangChain Docs](https://python.langchain.com/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Rails Guides](https://guides.rubyonrails.org/)
- [Docker Compose](https://docs.docker.com/compose/)

### Support
- **Issues**: File at GitHub repository issues page
- **Questions**: Review workplan FAQ sections
- **Updates**: Check master workplan for latest changes

## Success Metrics

Track your progress:

- [ ] **Phase 1 Complete**: All services running in Docker
- [ ] **Phase 2 Complete**: AI service generating lessons
- [ ] **Phase 3 Complete**: Rails API integrated with AI service
- [ ] **Phase 4 Complete**: ML models predicting engagement
- [ ] **Phase 5 Complete**: Deployed to AWS staging
- [ ] **Phase 6 Complete**: Security audit passed

### Demo Checkpoints

**After Phase 2**: Demo lesson generation via API
```bash
curl -X POST http://localhost:8000/api/v1/generate-lesson \
  -H "Content-Type: application/json" \
  -d '{"topic":"APR","learner_id":"demo"}'
```

**After Phase 3**: Demo end-to-end lesson delivery
```bash
# Request lesson via Rails API
curl -X POST http://localhost:3000/api/v1/learning_paths \
  -H "Content-Type: application/json" \
  -d '{"learner_id":"demo","topic":"credit_cards"}'
```

**After Phase 4**: Demo engagement prediction
```python
# In Python shell
from ml_pipeline.models.engagement_predictor import predict_engagement
predict_engagement(learner_id="demo", current_time="2025-11-15T14:00:00")
# Returns: {"optimal_time": "2025-11-15T16:30:00", "confidence": 0.85}
```

## Next Steps

**Right Now**:
1. Ensure all prerequisites are met (checklist above)
2. Read Phase 1 workplan: `docs/workplans/01-foundation-setup.md`
3. Start with Section 1.1: Create Directory Scaffold

**This Week**:
- Complete Phase 1, Sections 1-4 (structure, dependencies, Docker)

**Next Week**:
- Complete Phase 1, Sections 5-8 (CI/CD, docs, security)
- Begin Phase 2

**This Month**:
- Complete Phases 1-2
- Have working AI service generating lessons

---

**Remember**: This is a learning project. Take time to understand each component. The workplans are detailed for a reason - use them as your guide.

**Questions?** Review the relevant workplan section or architecture docs first. Most answers are already documented.

**Ready to start?** → Open `docs/workplans/01-foundation-setup.md` and begin!
