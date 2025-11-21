# Implement Adaptive Learning Agent for BMO Learning Platform

## Context
You are implementing the missing **Adaptive Learning Agent** functionality for the BMO Learning Platform. The project already has:
- ✅ FastAPI infrastructure (`app/main.py`)
- ✅ RAG pipeline with Chroma vector store (`app/ingestion/vector_store.py`)
- ✅ Lesson generator with safety checks (`app/generators/lesson_generator.py`)
- ✅ Document processing (`app/ingestion/document_processor.py`)
- ❌ **MISSING: Learning Orchestrator Agent** (agents directory is empty)

## Technical Stack
- LangChain 1.0.7 (use latest patterns, no deprecated APIs)
- **Anthropic Claude Haiku** (`claude-haiku-4-5-20251001`) for Agent LLM
- OpenAI `text-embedding-3-small` for Embeddings
- Python 3.11+
- FastAPI for endpoints
- Pydantic v2 for validation

## Progress Tracking

- [x] 1. Create Agent Tools (`app/ai_service/agents/tools.py`)
- [x] 2. Create Learning Orchestrator (`app/ai_service/agents/learning_orchestrator.py`)
- [x] 3. Add Memory Management (`app/ai_service/agents/memory_manager.py`)
- [x] 4. Create Agent API Endpoints (`app/ai_service/app/api/agent_routes.py`)
- [x] 5. Integration Points
- [x] 6. Testing Requirements
- [x] 7. Error Handling & Monitoring (Basic implementation complete)
- [ ] 8. Performance Optimizations (Future enhancement)
- [x] 9. Configuration Updates
- [x] 10. Documentation Requirements (Summary created)

## Implementation Status

**CORE IMPLEMENTATION: COMPLETE ✅**

All essential components have been implemented and tested:
- Agent tools with 6 core functions
- Learning orchestrator using LangChain 1.0.7
- Memory management with Redis
- API endpoints for agent interactions
- Comprehensive test coverage (15 tests passing)
- Integration with existing lesson generator and RAG pipeline

See [AGENT-IMPLEMENTATION-SUMMARY.md](../AGENT-IMPLEMENTATION-SUMMARY.md) for detailed implementation notes.

## Implementation Requirements

### 1. Create Agent Tools (`app/ai_service/agents/tools.py`)
Implement the following tools using LangChain's `@tool` decorator pattern:

```python
@tool(args_schema=AssessKnowledgeInput)
def assess_knowledge(learner_id: str, topic: str) -> dict:
    """Assess learner's current knowledge on a topic"""
    # Query learner progress from database
    # Return score, weak_areas, strong_areas

@tool(args_schema=GenerateLessonInput)
def generate_adaptive_lesson(topic: str, difficulty: str, learner_context: dict) -> dict:
    """Generate personalized lesson based on learner state"""
    # Call existing LessonGenerator
    # Adapt content based on difficulty and context
    
@tool
def create_practice_scenario(topic: str, industry_context: str, difficulty: str) -> str:
    """Create realistic work scenario for practice"""
    # Generate BMO-specific scenarios
    
@tool
def evaluate_quiz_response(response: str, expected_answer: str, topic: str) -> dict:
    """Evaluate learner response with feedback"""
    # Return: correct (bool), feedback, confidence_score, next_recommendation
    
@tool
def get_learning_path(learner_id: str, current_topic: str, performance: float) -> dict:
    """Determine next topics based on performance"""
    # Return: next_topic, difficulty_adjustment, reinforcement_needed
    
@tool
def track_engagement(learner_id: str, interaction_type: str, duration: int) -> dict:
    """Track learner engagement metrics"""
    # Log interaction, calculate engagement score
```

### 2. Create Learning Orchestrator (`app/ai_service/agents/learning_orchestrator.py`)
Build the main agent that orchestrates adaptive learning:

```python
class LearningOrchestrator:
    """Agent that orchestrates personalized learning paths"""
    
    def __init__(self):
        # Initialize with ChatAnthropic (Claude Haiku), temperature 0.3
        # Set up ConversationBufferMemory for context
        # Configure tools list
    
    def create_agent(self):
        """Create tool-calling agent with proper prompt"""
        # Use create_tool_calling_agent (LangChain 1.0.7 pattern)
        # Include MessagesPlaceholder for memory
        # Set max_iterations=5 to prevent loops
        
        # Agent System Prompt should include:
        # - Role: Adaptive learning assistant for BMO credit card training
        # - Process: Assess → Identify gaps → Generate lesson → Practice → Evaluate → Adjust
        # - Principles: Start easy, increase gradually, reinforce weak areas
        # - Constraints: 3-minute lessons max, use real BMO scenarios
        
    async def orchestrate_learning_session(self, learner_id: str, request: str) -> dict:
        """Handle complete learning interaction"""
        # Parse learner intent (new topic, quiz response, help request)
        # Execute agent with appropriate tools
        # Return structured response with lesson, quiz, next_steps
        
    async def adaptive_lesson_flow(self, learner_id: str, topic: str) -> dict:
        """Execute adaptive learning flow"""
        # 1. Assess current knowledge
        # 2. Determine appropriate difficulty
        # 3. Generate personalized lesson
        # 4. Create practice scenario
        # 5. Prepare assessment
        # Return complete learning package
```

### 3. Add Memory Management (`app/ai_service/agents/memory_manager.py`)
Implement conversation and learning history tracking:

```python
class LearningMemoryManager:
    """Manages learner conversation history and progress"""
    
    def __init__(self, redis_client):
        # Use Redis for persistent memory across sessions
        # Configure ConversationSummaryBufferMemory
        
    async def get_learner_context(self, learner_id: str) -> dict:
        """Retrieve learner's history and state"""
        # Last 10 interactions
        # Topics covered
        # Performance metrics
        # Learning preferences
        
    async def update_learner_progress(self, learner_id: str, interaction: dict):
        """Update learner's progress and history"""
        # Store interaction
        # Update performance metrics
        # Adjust difficulty preferences
```

### 4. Create Agent API Endpoints (`app/ai_service/app/api/agent_routes.py`)
Add new endpoints for agent interactions:

```python
@router.post("/agent/chat")
async def agent_chat(request: AgentChatRequest) -> AgentChatResponse:
    """Interactive chat with learning agent"""
    # Initialize orchestrator
    # Load learner context
    # Process request through agent
    # Return structured response
    
@router.post("/agent/start-lesson")
async def start_adaptive_lesson(request: StartLessonRequest) -> AdaptiveLessonResponse:
    """Start personalized lesson on topic"""
    # Assess knowledge
    # Generate adaptive content
    # Return lesson with quiz
    
@router.post("/agent/submit-answer")
async def submit_quiz_answer(request: QuizAnswerRequest) -> FeedbackResponse:
    """Process quiz answer with feedback"""
    # Evaluate response
    # Generate feedback
    # Recommend next action
    
@router.get("/agent/learning-path/{learner_id}")
async def get_personalized_path(learner_id: str) -> LearningPathResponse:
    """Get personalized learning path"""
    # Analyze progress
    # Identify gaps
    # Return recommended sequence
```

### 5. Integration Points

#### Connect to Existing Components:
1. **LessonGenerator**: Agent should call existing generator with learner context
2. **VectorStore**: Agent queries relevant documents for personalized content
3. **SafetyValidator**: All agent responses pass through safety checks
4. **Settings**: Use existing configuration for models and limits

#### Database Schema (add to Rails):
```ruby
# app/rails_api/db/migrate/xxx_add_agent_tables.rb
create_table :learner_interactions do |t|
  t.references :learner
  t.string :interaction_type # chat, quiz, lesson
  t.jsonb :request_data
  t.jsonb :agent_response
  t.jsonb :tool_calls # which tools were used
  t.float :performance_score
  t.timestamps
end

create_table :learning_paths do |t|
  t.references :learner
  t.jsonb :completed_topics
  t.jsonb :skill_levels # {topic: level}
  t.jsonb :weak_areas
  t.string :current_topic
  t.string :next_recommended
  t.timestamps
end
```

### 6. Testing Requirements

Create comprehensive tests:

```python
# tests/ai_service/unit/test_agent_tools.py
def test_assess_knowledge_returns_score():
    # Mock database query
    # Verify score calculation

def test_generate_adaptive_lesson_adjusts_difficulty():
    # Test easy, medium, hard variations
    # Verify content adaptation

# tests/ai_service/unit/test_learning_orchestrator.py
@pytest.mark.asyncio
async def test_orchestrator_executes_tool_sequence():
    # Mock tool calls
    # Verify correct sequence: assess → generate → evaluate

async def test_orchestrator_handles_memory():
    # Verify conversation context maintained
    # Check memory updates

# tests/ai_service/integration/test_agent_flow.py
async def test_complete_learning_flow():
    # Test full flow from assessment to completion
    # Verify adaptation based on performance
```

### 7. Error Handling & Monitoring

Add robust error handling:
```python
class AgentError(Exception):
    """Base exception for agent errors"""

class ToolExecutionError(AgentError):
    """Tool failed to execute"""

class LearnerContextError(AgentError):
    """Failed to load learner context"""

# In orchestrator:
try:
    result = await agent.ainvoke(request)
except ToolException as e:
    logger.error(f"Tool execution failed: {e}")
    return fallback_response()
```

### 8. Performance Optimizations

1. **Cache tool results**: Use Redis to cache assessment scores (5 min TTL)
2. **Batch database queries**: Load learner context in single query
3. **Limit agent iterations**: Set max_iterations=5 to prevent infinite loops
4. **Stream responses**: Use FastAPI streaming for real-time agent responses

### 9. Configuration Updates

Update `.env` and settings:
```python
# app/ai_service/app/config/settings.py
anthropic_model: str = "claude-haiku-4-5-20251001"
agent_temperature: float = 0.3
agent_max_iterations: int = 5
enable_agent_memory: bool = True
memory_window_size: int = 10
```

### 10. Documentation Requirements

1. **API Documentation**: Add OpenAPI schemas for all agent endpoints
2. **Architecture Decision Record**: Document why tool-calling agent vs ReAct
3. **Tool Descriptions**: Clear docstrings for LLM understanding
4. **Integration Guide**: How Rails API calls agent endpoints
5. **Agent Flow Diagram**: Visualizing the decision process

## Validation Criteria

Your implementation is complete when:

1. ✅ Agent successfully assesses knowledge and adapts difficulty
2. ✅ Conversation memory persists across sessions
3. ✅ Tools execute in correct sequence based on learner needs
4. ✅ API endpoints return structured responses
5. ✅ All tests pass with >80% coverage
6. ✅ Agent handles errors gracefully with fallbacks
7. ✅ Responses pass safety validation
8. ✅ Performance: <2s response time for agent interactions

## Code Quality Requirements

- Use type hints throughout
- Add comprehensive docstrings
- Follow existing project structure
- Use structured logging with context
- Handle all edge cases (empty responses, API failures)
- No deprecated LangChain APIs (check v1.0.7 docs)

## Example Agent Interaction Flow

```python
# User: "I want to learn about APR"
# Agent executes:
1. assess_knowledge(learner_id, "APR") → score: 0.3 (beginner)
2. generate_adaptive_lesson("APR", "easy", context) → basic lesson
3. create_practice_scenario("APR", "retail", "easy") → scenario
4. Returns: lesson + scenario + quiz

# User: "The answer is B"
# Agent executes:
1. evaluate_quiz_response("B", "B", "APR") → correct: true
2. get_learning_path(learner_id, "APR", 1.0) → next: "compound interest"
3. Returns: feedback + next topic recommendation

# User: "That's confusing, can you explain differently?"
# Agent executes:
1. Accesses memory of previous explanation
2. generate_adaptive_lesson("APR", "easy", alternative_style)
3. Returns: simplified explanation with analogy
```

## Priority Order

1. **First**: Implement basic tools (assess, generate, evaluate)
2. **Second**: Create orchestrator with memory
3. **Third**: Add API endpoints
4. **Fourth**: Integrate with existing components
5. **Fifth**: Add tests and error handling
6. **Sixth**: Optimize performance

## Additional Notes

- The agent should feel conversational but stay focused on learning objectives
- Every interaction should move the learner forward in their journey
- Use existing BMO credit card context from training materials
- Agent should recognize when learner is struggling and automatically adjust
- Include encouragement and progress tracking in responses

Remember: This agent is the core differentiator of the platform. It should demonstrate advanced LangChain patterns while delivering real educational value through personalization.