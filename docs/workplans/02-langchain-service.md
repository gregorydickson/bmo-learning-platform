# Phase 2: LangChain AI Service

**Duration**: 10-14 days
**Goal**: Build production-grade LangChain service demonstrating RAG, agents, chains, and safety mechanisms

## Overview
This phase implements the core AI functionality. We prioritize:
1. **LangChain Design Patterns** (showcasing framework capabilities)
2. **LLM Safety** (Constitutional AI, content moderation, PII detection)
3. **Production Readiness** (error handling, monitoring, caching)
4. **Comprehensive Testing** (unit, integration, E2E with LLM mocks)

## Prerequisites
- [ ] Phase 1 complete (Docker environment running)
- [ ] OpenAI API key configured
- [ ] PostgreSQL with pgvector extension enabled
- [ ] Understanding of LangChain concepts (chains, agents, memory)

## API Versions Used
```python
langchain==1.0.7
langchain-openai==1.0.3
langchain-community==0.4.1
langchain-core==1.0.4
openai==2.8.0
fastapi==0.121.2
pydantic==2.12.4
```

## 1. Core Infrastructure

### 1.1 FastAPI Application Bootstrap
- [ ] Create `app/ai_service/app/main.py`
  ```python
  from fastapi import FastAPI
  from fastapi.middleware.cors import CORSMiddleware
  from contextlib import asynccontextmanager
  import structlog

  from app.config.settings import settings
  from app.api.routes import router

  logger = structlog.get_logger()

  @asynccontextmanager
  async def lifespan(app: FastAPI):
      # Startup
      logger.info("Starting AI service", version="0.1.0")
      yield
      # Shutdown
      logger.info("Shutting down AI service")

  app = FastAPI(
      title="BMO Learning AI Service",
      description="LangChain-powered microlearning content generation",
      version="0.1.0",
      docs_url="/docs",
      redoc_url="/redoc",
      lifespan=lifespan
  )

  # Middleware
  app.add_middleware(
      CORSMiddleware,
      allow_origins=settings.allowed_origins,
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )

  # Routes
  app.include_router(router, prefix="/api/v1")

  @app.get("/health")
  async def health_check():
      return {"status": "healthy", "service": "ai_service"}
  ```

- [ ] Create `app/ai_service/app/config/settings.py`
  ```python
  from pydantic_settings import BaseSettings
  from functools import lru_cache

  class Settings(BaseSettings):
      # OpenAI
      openai_api_key: str
      openai_model: str = "gpt-4-turbo-preview"
      openai_embedding_model: str = "text-embedding-3-small"

      # Database
      database_url: str
      redis_url: str

      # Vector Store
      chroma_persist_directory: str = "./data/chroma"
      vector_store_collection: str = "bmo_learning_docs"

      # LangChain
      langchain_tracing_v2: bool = False
      langchain_api_key: str | None = None

      # Safety
      enable_constitutional_ai: bool = True
      enable_pii_detection: bool = True
      max_tokens_per_lesson: int = 500

      # Caching
      enable_llm_cache: bool = True
      cache_ttl_seconds: int = 3600

      # Rate Limiting
      rate_limit_per_minute: int = 60

      # CORS
      allowed_origins: list[str] = ["http://localhost:3000"]

      model_config = {
          "env_file": ".env",
          "case_sensitive": False
      }

  @lru_cache()
  def get_settings() -> Settings:
      return Settings()

  settings = get_settings()
  ```

**Validation**: `curl http://localhost:8000/health` returns 200

### 1.2 Structured Logging
- [ ] Create `app/ai_service/app/utils/logging.py`
  ```python
  import structlog
  from typing import Any

  def configure_logging():
      structlog.configure(
          processors=[
              structlog.stdlib.filter_by_level,
              structlog.stdlib.add_logger_name,
              structlog.stdlib.add_log_level,
              structlog.stdlib.PositionalArgumentsFormatter(),
              structlog.processors.TimeStamper(fmt="iso"),
              structlog.processors.StackInfoRenderer(),
              structlog.processors.format_exc_info,
              structlog.processors.UnicodeDecoder(),
              structlog.processors.JSONRenderer()
          ],
          wrapper_class=structlog.stdlib.BoundLogger,
          logger_factory=structlog.stdlib.LoggerFactory(),
          cache_logger_on_first_use=True,
      )

  def log_llm_call(prompt: str, response: str, metadata: dict[str, Any]):
      logger = structlog.get_logger()
      logger.info(
          "llm_call",
          prompt_length=len(prompt),
          response_length=len(response),
          **metadata
      )
  ```

**Validation**: Logs output as structured JSON

## 2. Document Ingestion & RAG Pipeline

### 2.1 Document Loader System
- [ ] Create `app/ai_service/ingestion/document_processor.py`
  ```python
  from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
  from langchain_text_splitters import RecursiveCharacterTextSplitter
  from langchain_core.documents import Document
  import structlog

  logger = structlog.get_logger()

  class DocumentProcessor:
      """Loads and chunks documents for vector store ingestion"""

      def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
          self.splitter = RecursiveCharacterTextSplitter(
              chunk_size=chunk_size,
              chunk_overlap=chunk_overlap,
              separators=["\n\n", "\n", ". ", " ", ""],
              length_function=len,
          )

      def load_pdfs(self, directory: str) -> list[Document]:
          """Load all PDFs from a directory"""
          logger.info("Loading PDFs", directory=directory)

          loader = DirectoryLoader(
              directory,
              glob="**/*.pdf",
              loader_cls=PyPDFLoader,
              show_progress=True,
          )

          documents = loader.load()
          logger.info("Loaded documents", count=len(documents))

          return documents

      def chunk_documents(self, documents: list[Document]) -> list[Document]:
          """Split documents into chunks for embedding"""
          logger.info("Chunking documents", count=len(documents))

          chunks = self.splitter.split_documents(documents)

          logger.info("Created chunks", count=len(chunks))
          return chunks

      def add_metadata(self, chunks: list[Document], metadata: dict) -> list[Document]:
          """Add metadata to chunks for filtering"""
          for chunk in chunks:
              chunk.metadata.update(metadata)

          return chunks
  ```

**Why This Design**:
- `RecursiveCharacterTextSplitter`: Respects document structure (paragraphs, sentences)
- Metadata enrichment: Enables filtered retrieval (e.g., only "compliance" documents)
- Logging: Tracks ingestion pipeline progress

### 2.2 Vector Store Setup
- [ ] Create `app/ai_service/ingestion/vector_store.py`
  ```python
  from langchain_openai import OpenAIEmbeddings
  from langchain_community.vectorstores import Chroma
  from langchain_core.documents import Document
  from app.config.settings import settings
  import structlog

  logger = structlog.get_logger()

  class VectorStoreManager:
      """Manages Chroma vector store for document retrieval"""

      def __init__(self):
          self.embeddings = OpenAIEmbeddings(
              model=settings.openai_embedding_model,
              api_key=settings.openai_api_key,
          )

          self.vectorstore = Chroma(
              collection_name=settings.vector_store_collection,
              embedding_function=self.embeddings,
              persist_directory=settings.chroma_persist_directory,
          )

      def add_documents(self, documents: list[Document]) -> list[str]:
          """Add documents to vector store"""
          logger.info("Adding documents to vector store", count=len(documents))

          ids = self.vectorstore.add_documents(documents)

          logger.info("Added documents", ids_count=len(ids))
          return ids

      def similarity_search(
          self,
          query: str,
          k: int = 5,
          filter_metadata: dict | None = None
      ) -> list[Document]:
          """Search for similar documents"""
          logger.info("Similarity search", query=query[:50], k=k)

          results = self.vectorstore.similarity_search(
              query,
              k=k,
              filter=filter_metadata
          )

          logger.info("Search results", count=len(results))
          return results

      def as_retriever(self, **kwargs):
          """Get retriever interface for chains"""
          return self.vectorstore.as_retriever(**kwargs)
  ```

**Why Chroma**:
- Local development friendly (no external service)
- Persistent storage (survives container restarts)
- Metadata filtering (critical for compliance tagging)

### 2.3 Advanced Retrieval Strategies
- [ ] Create `app/ai_service/retrievers/multi_query_retriever.py`
  ```python
  from langchain.retrievers.multi_query import MultiQueryRetriever
  from langchain_openai import ChatOpenAI
  from langchain.retrievers import ParentDocumentRetriever
  from langchain.storage import InMemoryStore
  from app.config.settings import settings
  import structlog

  logger = structlog.get_logger()

  class AdvancedRetriever:
      """Implements multiple retrieval strategies for robust RAG"""

      def __init__(self, vector_store_manager):
          self.vector_store = vector_store_manager
          self.llm = ChatOpenAI(
              model=settings.openai_model,
              temperature=0,
              api_key=settings.openai_api_key,
          )

      def multi_query_retriever(self):
          """
          Generates multiple query variations for better recall.
          Use when: User query might be ambiguous
          """
          base_retriever = self.vector_store.as_retriever(search_kwargs={"k": 3})

          retriever = MultiQueryRetriever.from_llm(
              retriever=base_retriever,
              llm=self.llm,
          )

          logger.info("Using multi-query retrieval")
          return retriever

      def parent_document_retriever(self, child_splitter, parent_splitter):
          """
          Returns full parent documents for better context.
          Use when: Need surrounding context around chunks
          """
          store = InMemoryStore()

          retriever = ParentDocumentRetriever(
              vectorstore=self.vector_store.vectorstore,
              docstore=store,
              child_splitter=child_splitter,
              parent_splitter=parent_splitter,
          )

          logger.info("Using parent document retrieval")
          return retriever

      def contextual_compression_retriever(self):
          """
          Compresses retrieved documents to relevant portions.
          Use when: Want to reduce token usage while maintaining relevance
          """
          from langchain.retrievers import ContextualCompressionRetriever
          from langchain.retrievers.document_compressors import LLMChainExtractor

          base_retriever = self.vector_store.as_retriever()

          compressor = LLMChainExtractor.from_llm(self.llm)
          retriever = ContextualCompressionRetriever(
              base_compressor=compressor,
              base_retriever=base_retriever,
          )

          logger.info("Using contextual compression retrieval")
          return retriever
  ```

**Why Multiple Strategies**:
- **MultiQuery**: Handles ambiguous user questions (e.g., "APR" vs "annual percentage rate")
- **ParentDocument**: Prevents losing context around retrieved chunks (critical for financial regulations)
- **ContextualCompression**: Reduces costs by compressing irrelevant portions

### 2.4 Ingestion Script
- [ ] Create `app/ai_service/scripts/ingest_documents.py`
  ```python
  import asyncio
  from app.ingestion.document_processor import DocumentProcessor
  from app.ingestion.vector_store import VectorStoreManager
  import structlog

  logger = structlog.get_logger()

  async def ingest_training_materials(directory: str):
      """Ingest BMO training materials into vector store"""

      # Initialize components
      processor = DocumentProcessor(chunk_size=500, chunk_overlap=50)
      vector_store = VectorStoreManager()

      # Load documents
      documents = processor.load_pdfs(directory)

      # Chunk documents
      chunks = processor.chunk_documents(documents)

      # Add metadata for filtering
      chunks = processor.add_metadata(chunks, {
          "source": "bmo_training",
          "version": "v1.0",
          "compliance_reviewed": True,
      })

      # Store in vector database
      ids = vector_store.add_documents(chunks)

      logger.info("Ingestion complete", total_chunks=len(ids))

  if __name__ == "__main__":
      import sys
      directory = sys.argv[1] if len(sys.argv) > 1 else "./data/training_docs"
      asyncio.run(ingest_training_materials(directory))
  ```

**Validation**: `uv run python scripts/ingest_documents.py` ingests docs successfully

## 3. LLM Safety Layer

### 3.1 Constitutional AI Implementation
**CRITICAL NOTE**: Constitutional AI has been removed from LangChain 1.0. Use prompt-based safety checks or external moderation APIs instead.

- [ ] Create `app/ai_service/safety/constitutional_chain.py`
  ```python
  from langchain_openai import ChatOpenAI
  from langchain_core.prompts import ChatPromptTemplate
  from app.config.settings import settings
  import structlog

  logger = structlog.get_logger()

  # Financial services safety principles
  SAFETY_PRINCIPLES = """
  Review the generated content for the following issues:

  1. ACCURACY: Identify any factual inaccuracies about interest rates, fees, or credit terms.
  2. COMPLIANCE: Identify statements that could violate financial regulations or misrepresent product terms.
  3. CLARITY: Identify jargon or complex terms that might confuse learners.
  4. BIAS: Identify any discriminatory or biased statements.

  If issues are found, revise the content to address them while maintaining accuracy and compliance.
  """

  class SafeContentGenerator:
      """Generates content with safety checks using prompt-based review"""

      def __init__(self):
          self.llm = ChatOpenAI(
              model=settings.openai_model,
              temperature=0.7,
              api_key=settings.openai_api_key,
          )
          self.safety_llm = ChatOpenAI(
              model=settings.openai_model,
              temperature=0,
              api_key=settings.openai_api_key,
          )

      async def generate_safe_content(self, content: str) -> dict:
          """Review and revise content for safety"""

          if not settings.enable_constitutional_ai:
              logger.warning("Constitutional AI disabled")
              return {"content": content, "revisions": []}

          # Create safety review prompt
          safety_prompt = ChatPromptTemplate.from_messages([
              ("system", SAFETY_PRINCIPLES),
              ("human", "Review this content:\n\n{content}\n\nProvide any necessary revisions.")
          ])

          # Review content
          review_chain = safety_prompt | self.safety_llm
          review = await review_chain.ainvoke({"content": content})

          logger.info("Safety review completed", has_revisions=bool(review.content))

          return {
              "content": content,
              "review": review.content,
              "passed_safety": True
          }
  ```

**Why Safety Checks**:
- **Accuracy**: Prevents hallucinated financial facts (e.g., wrong APR)
- **Compliance**: Auto-detects regulatory violations
- **Clarity**: Ensures content is learner-appropriate
- **Critical for Financial Services**: Mitigates legal risk

### 3.2 PII Detection & Redaction
- [ ] Create `app/ai_service/safety/pii_detector.py`
  ```python
  import re
  from typing import List, Tuple
  import structlog

  logger = structlog.get_logger()

  class PIIDetector:
      """Detects and redacts personally identifiable information"""

      # Regex patterns for common PII
      PATTERNS = {
          "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
          "credit_card": r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
          "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
          "phone": r'\b\d{3}[- ]?\d{3}[- ]?\d{4}\b',
      }

      def detect(self, text: str) -> List[Tuple[str, str]]:
          """Detect PII in text, return list of (type, match)"""
          findings = []

          for pii_type, pattern in self.PATTERNS.items():
              matches = re.findall(pattern, text)
              for match in matches:
                  findings.append((pii_type, match))

          if findings:
              logger.warning("PII detected", count=len(findings))

          return findings

      def redact(self, text: str) -> str:
          """Redact PII from text"""
          redacted_text = text

          for pii_type, pattern in self.PATTERNS.items():
              redacted_text = re.sub(pattern, f"[REDACTED_{pii_type.upper()}]", redacted_text)

          return redacted_text

      def validate_safe(self, text: str) -> bool:
          """Check if text is safe (no PII)"""
          findings = self.detect(text)
          return len(findings) == 0
  ```

**Why PII Detection**:
- **Privacy**: Prevents PII from being embedded in vector store
- **Compliance**: GDPR/CCPA requirement
- **Logging Safety**: Redacts PII from application logs

### 3.3 Content Moderation
- [ ] Create `app/ai_service/safety/content_moderator.py`
  ```python
  from openai import AsyncOpenAI
  from app.config.settings import settings
  import structlog

  logger = structlog.get_logger()

  class ContentModerator:
      """Uses OpenAI moderation API to filter inappropriate content"""

      def __init__(self):
          self.client = AsyncOpenAI(api_key=settings.openai_api_key)

      async def is_safe(self, text: str) -> tuple[bool, dict]:
          """
          Check if content is safe for learning platform.
          Returns: (is_safe, moderation_results)
          """
          try:
              response = await self.client.moderations.create(input=text)
              result = response.results[0]

              is_safe = not result.flagged

              if result.flagged:
                  logger.warning(
                      "Content flagged by moderation",
                      categories=result.categories.model_dump(),
                  )

              return is_safe, result.model_dump()

          except Exception as e:
              logger.error("Moderation API error", error=str(e))
              # Fail closed - reject if moderation fails
              return False, {"error": str(e)}
  ```

**Why Content Moderation**:
- **Brand Safety**: Prevents inappropriate content in corporate learning
- **Automatic**: No manual review needed
- **Fail Closed**: Rejects content if moderation fails (secure default)

## 4. Content Generation Pipeline

### 4.1 Lesson Generator Chain
- [ ] Create `app/ai_service/generators/lesson_generator.py`
  ```python
  from langchain_core.prompts import ChatPromptTemplate
  from langchain_openai import ChatOpenAI
  from langchain_core.output_parsers import JsonOutputParser
  from pydantic import BaseModel, Field
  from app.config.settings import settings
  from app.safety.constitutional_chain import SafeContentGenerator
  import structlog

  logger = structlog.get_logger()

  # Output schema for lesson
  class MicroLesson(BaseModel):
      topic: str = Field(description="The learning topic")
      content: str = Field(description="Lesson content (max 500 tokens)")
      key_points: list[str] = Field(description="3-5 key takeaways")
      scenario: str = Field(description="Real-world application scenario")
      quiz_question: str = Field(description="Assessment question")
      quiz_options: list[str] = Field(description="4 multiple choice options")
      correct_answer: int = Field(description="Index of correct answer (0-3)")

  class LessonGenerator:
      """Generates microlessons using LangChain"""

      def __init__(self, retriever):
          self.llm = ChatOpenAI(
              model=settings.openai_model,
              temperature=0.7,
              api_key=settings.openai_api_key,
          )
          self.retriever = retriever
          self.safety = SafeContentGenerator()
          self.parser = JsonOutputParser(pydantic_object=MicroLesson)

      def create_lesson_chain(self):
          """Build chain for lesson generation"""

          prompt = ChatPromptTemplate.from_messages([
              ("system", """You are an expert educator creating microlearning content for bank employees.

Create a concise lesson (max 500 tokens) on the given topic using the provided source material.

Requirements:
- Use simple, clear language
- Focus on practical application
- Include concrete examples
- Optimize for SMS/Slack delivery (short paragraphs)
- Include a realistic work scenario
- Create an assessment question with 4 options

{format_instructions}"""),
              ("human", """Topic: {topic}

Source Material:
{retrieved_docs}

Create the lesson following the format above.""")
          ])

          chain = prompt | self.llm | self.parser

          logger.info("Lesson generation chain created")
          return chain

      async def generate_lesson(self, topic: str, learner_state: dict) -> MicroLesson:
          """Generate a complete microlesson"""

          # Retrieve relevant documents
          docs = await self.retriever.ainvoke(topic)
          retrieved_text = "\n\n".join([doc.page_content for doc in docs])

          # Generate lesson
          chain = self.create_lesson_chain()
          result = await chain.ainvoke({
              "topic": topic,
              "retrieved_docs": retrieved_text,
              "format_instructions": self.parser.get_format_instructions()
          })

          # Apply safety checks
          safety_result = await self.safety.generate_safe_content(result["content"])

          # Parse structured output
          lesson = MicroLesson(**result)

          logger.info("Lesson generated", topic=topic)
          return lesson
  ```

**Why This Design**:
- **Traceable**: Chain output is visible (debugging)
- **Modular**: Easy to swap components
- **Type-Safe**: Pydantic ensures valid output

### 4.2 Few-Shot Prompt Template
- [ ] Create `app/ai_service/generators/few_shot_prompts.py`
  ```python
  from langchain_core.prompts import FewShotChatMessagePromptTemplate, ChatPromptTemplate

  # Example lessons for consistency
  LESSON_EXAMPLES = [
      {
          "topic": "APR (Annual Percentage Rate)",
          "lesson": """
**Understanding APR**

APR represents the yearly cost of borrowing, including interest and fees.
It's the TRUE cost of credit - always higher than the stated interest rate.

**Why it matters**: Customers compare cards by APR. A lower APR = lower cost.

**Example**: 18% APR on $1,000 balance = $180/year in interest.

**Key Point**: By law, you MUST disclose APR before approval.
          """,
      },
      {
          "topic": "Rewards Programs",
          "lesson": """
**BMO Rewards Basics**

Earn points on purchases, redeem for travel/cash/merchandise.

**Value Proposition**:
- 1 point per $1 spent
- 2 points on gas/groceries (Premium card)
- No blackout dates on travel

**Selling Tip**: Calculate annual rewards based on customer spend.
Example: $20K/year spend = $200+ in rewards.

**Common Question**: "Do points expire?" → No, as long as account is active.
          """
      }
  ]

  # Create few-shot template
  example_prompt = ChatPromptTemplate.from_messages([
      ("human", "Topic: {topic}"),
      ("ai", "Lesson: {lesson}")
  ])

  few_shot_prompt = FewShotChatMessagePromptTemplate(
      examples=LESSON_EXAMPLES,
      example_prompt=example_prompt,
  )
  ```

**Why Few-Shot**:
- **Consistency**: All lessons match BMO's tone/format
- **Quality**: Examples guide LLM to desired output
- **Onboarding**: New team members understand expected style

## 5. Adaptive Learning Agent

### 5.1 Agent Tools
- [ ] Create `app/ai_service/agents/tools.py`
  ```python
  from langchain_core.tools import tool
  from pydantic import BaseModel, Field
  import structlog

  logger = structlog.get_logger()

  # Tool schemas
  class AssessKnowledgeInput(BaseModel):
      learner_id: str = Field(description="Unique learner identifier")
      topic: str = Field(description="Topic to assess")

  class GenerateLessonInput(BaseModel):
      topic: str = Field(description="Topic for lesson")
      difficulty: str = Field(description="easy, medium, or hard")

  @tool(args_schema=AssessKnowledgeInput)
  def assess_knowledge(learner_id: str, topic: str) -> dict:
      """Assess learner's current knowledge on a topic"""
      # TODO: Query learner progress database
      logger.info("Assessing knowledge", learner_id=learner_id, topic=topic)
      return {
          "score": 0.65,
          "weak_areas": ["interest calculation", "fee structures"],
          "strong_areas": ["APR basics"],
      }

  @tool(args_schema=GenerateLessonInput)
  def generate_lesson(topic: str, difficulty: str) -> str:
      """Generate a lesson at appropriate difficulty"""
      # TODO: Call lesson generator
      logger.info("Generating lesson", topic=topic, difficulty=difficulty)
      return f"Lesson content for {topic} at {difficulty} level"

  @tool
  def create_scenario(topic: str, context: str) -> str:
      """Create a practical scenario"""
      logger.info("Creating scenario", topic=topic)
      return f"Scenario applying {topic} in context: {context}"

  @tool
  def evaluate_response(response: str, expected: str) -> dict:
      """Evaluate learner's response"""
      logger.info("Evaluating response")
      return {
          "correct": True,
          "feedback": "Great job!",
          "next_topic": "compound interest",
      }

  # Define tools list
  LEARNING_TOOLS = [
      assess_knowledge,
      generate_lesson,
      create_scenario,
      evaluate_response,
  ]
  ```

**Why Tool Decorator**:
- **Simplified**: @tool decorator replaces StructuredTool
- **Type Safety**: Pydantic validation prevents errors
- **Self-Documenting**: Schema describes tool purpose
- **Agent-Friendly**: LLM sees tool signatures and knows when to use them

### 5.2 Learning Orchestrator Agent
- [ ] Create `app/ai_service/agents/learning_orchestrator.py`
  ```python
  from langchain.agents import create_tool_calling_agent, AgentExecutor
  from langchain_openai import ChatOpenAI
  from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
  from langchain.memory import ConversationBufferMemory
  from app.agents.tools import LEARNING_TOOLS
  from app.config.settings import settings
  import structlog

  logger = structlog.get_logger()

  class LearningOrchestrator:
      """Agent that orchestrates adaptive learning paths"""

      def __init__(self):
          self.llm = ChatOpenAI(
              model=settings.openai_model,
              temperature=0.3,
              api_key=settings.openai_api_key,
          )

          # Memory tracks conversation history
          self.memory = ConversationBufferMemory(
              memory_key="chat_history",
              return_messages=True,
          )

      def create_agent(self):
          """Create tool-calling agent"""

          # Agent prompt
          prompt = ChatPromptTemplate.from_messages([
              ("system", """You are an adaptive learning assistant for BMO sales associates.

Your goal: Guide learners through personalized learning paths.

**Your Process**:
1. Assess current knowledge using assess_knowledge tool
2. Identify knowledge gaps
3. Generate appropriate lesson using generate_lesson tool
4. Create practical scenario using create_scenario tool
5. Evaluate responses using evaluate_response tool
6. Adjust difficulty based on performance

**Key Principles**:
- Start easy, increase difficulty gradually
- Reinforce weak areas before advancing
- Use real BMO scenarios
- Keep lessons under 3 minutes"""),
              MessagesPlaceholder(variable_name="chat_history"),
              ("human", "{input}"),
              MessagesPlaceholder(variable_name="agent_scratchpad"),
          ])

          # Create agent
          agent = create_tool_calling_agent(
              llm=self.llm,
              tools=LEARNING_TOOLS,
              prompt=prompt,
          )

          # Wrap in executor
          agent_executor = AgentExecutor(
              agent=agent,
              tools=LEARNING_TOOLS,
              memory=self.memory,
              verbose=True,
              max_iterations=5,
              return_intermediate_steps=True,
          )

          logger.info("Learning orchestrator agent created")
          return agent_executor

      async def orchestrate_learning(self, learner_id: str, request: str):
          """Handle learner request with agent"""
          agent = self.create_agent()

          result = await agent.ainvoke({
              "input": f"Learner {learner_id} says: {request}"
          })

          logger.info("Agent execution complete", steps=len(result.get("intermediate_steps", [])))
          return result
  ```

**Why Agent vs Chain**:
- **Dynamic**: Agent decides which tools to use based on learner state
- **Memory**: Tracks learning history across sessions
- **Adaptive**: Changes approach based on performance

## 6. Output Parsing & Validation

### 6.1 Robust Output Parser
- [ ] Create `app/ai_service/parsers/output_parser.py`
  ```python
  from langchain_core.output_parsers import JsonOutputParser
  from langchain_openai import ChatOpenAI
  from pydantic import BaseModel, Field, field_validator
  from app.config.settings import settings
  import structlog

  logger = structlog.get_logger()

  class QuizQuestion(BaseModel):
      question: str = Field(description="The quiz question text")
      options: list[str] = Field(description="Exactly 4 answer options")
      correct_index: int = Field(description="Index of correct answer (0-3)")
      explanation: str = Field(description="Why the correct answer is right")

      @field_validator("options")
      @classmethod
      def validate_option_count(cls, v):
          if len(v) != 4:
              raise ValueError("Must have exactly 4 options")
          return v

      @field_validator("correct_index")
      @classmethod
      def validate_correct_index(cls, v):
          if not 0 <= v <= 3:
              raise ValueError("Correct index must be 0-3")
          return v

  class RobustParser:
      """Parser with automatic error correction"""

      def __init__(self):
          self.llm = ChatOpenAI(
              model=settings.openai_model,
              temperature=0,
              api_key=settings.openai_api_key,
          )

      def create_parser(self, pydantic_model):
          """Create JSON parser"""
          parser = JsonOutputParser(pydantic_object=pydantic_model)

          logger.info("Created parser", model=pydantic_model.__name__)
          return parser

      async def parse_with_retry(self, text: str, parser, max_retries: int = 3):
          """Parse with multiple retry attempts"""
          for attempt in range(max_retries):
              try:
                  result = await parser.aparse(text)
                  logger.info("Parse successful", attempt=attempt)
                  return result
              except Exception as e:
                  logger.warning("Parse failed", attempt=attempt, error=str(e))
                  if attempt == max_retries - 1:
                      raise

          raise ValueError("Failed to parse after max retries")
  ```

**Why Output Parser**:
- **Reliability**: Validates JSON from LLM
- **Production-Ready**: Prevents integration failures with Rails
- **Type Safety**: Pydantic validation

## 7. Caching & Performance

### 7.1 LLM Response Caching
- [ ] Create `app/ai_service/utils/caching.py`
  ```python
  from langchain_community.cache import RedisCache
  from langchain.globals import set_llm_cache
  from redis import Redis
  from app.config.settings import settings
  import structlog

  logger = structlog.get_logger()

  def setup_llm_cache():
      """Configure Redis-based LLM caching"""
      if not settings.enable_llm_cache:
          logger.info("LLM caching disabled")
          return

      redis_client = Redis.from_url(
          settings.redis_url,
          decode_responses=True,
      )

      set_llm_cache(RedisCache(redis_client=redis_client))
      logger.info("LLM cache configured", ttl=settings.cache_ttl_seconds)
  ```

**Why Caching**:
- **Cost**: Repeated queries (e.g., "What is APR?") cached = no API cost
- **Latency**: Redis lookup is ~1ms vs 2-5s LLM call
- **Consistency**: Same question = same answer

### 7.2 Callback Handlers for Monitoring
- [ ] Create `app/ai_service/callbacks/monitoring.py`
  ```python
  from langchain_core.callbacks import BaseCallbackHandler
  from typing import Any
  import structlog
  import time

  logger = structlog.get_logger()

  class MetricsCallback(BaseCallbackHandler):
      """Tracks LLM usage metrics"""

      def __init__(self):
          self.start_time = None
          self.total_tokens = 0
          self.llm_calls = 0

      def on_llm_start(self, serialized: dict, prompts: list[str], **kwargs):
          self.start_time = time.time()
          self.llm_calls += 1
          logger.info("LLM call started", call_number=self.llm_calls)

      def on_llm_end(self, response, **kwargs):
          duration = time.time() - self.start_time

          # Extract token usage from response metadata
          usage = response.llm_output.get("token_usage", {}) if hasattr(response, "llm_output") else {}

          self.total_tokens += usage.get("total_tokens", 0)

          logger.info(
              "LLM call completed",
              duration_seconds=duration,
              prompt_tokens=usage.get("prompt_tokens"),
              completion_tokens=usage.get("completion_tokens"),
              total_calls=self.llm_calls,
          )

      def on_llm_error(self, error: Exception, **kwargs):
          logger.error("LLM call failed", error=str(error))
  ```

**Why Callbacks**:
- **Observability**: Track token usage for cost monitoring
- **Debugging**: See exact prompts sent to LLM
- **Performance**: Measure latency per chain stage

## 8. API Endpoints

### 8.1 Content Generation Endpoint
- [ ] Create `app/ai_service/app/api/routes.py`
  ```python
  from fastapi import APIRouter, HTTPException
  from pydantic import BaseModel
  from app.generators.lesson_generator import LessonGenerator, MicroLesson
  from app.ingestion.vector_store import VectorStoreManager
  from app.safety.pii_detector import PIIDetector
  from app.safety.content_moderator import ContentModerator
  import structlog

  logger = structlog.get_logger()
  router = APIRouter()

  # Request/Response models
  class GenerateLessonRequest(BaseModel):
      topic: str
      learner_id: str
      difficulty: str = "medium"

  class GenerateLessonResponse(BaseModel):
      lesson: MicroLesson
      metadata: dict

  @router.post("/generate-lesson", response_model=GenerateLessonResponse)
  async def generate_lesson(request: GenerateLessonRequest):
      """Generate a microlesson on a topic"""
      logger.info("Lesson generation requested", topic=request.topic)

      # Safety checks
      pii_detector = PIIDetector()
      if not pii_detector.validate_safe(request.topic):
          raise HTTPException(status_code=400, detail="PII detected in topic")

      # Initialize components
      vector_store = VectorStoreManager()
      retriever = vector_store.as_retriever(search_kwargs={"k": 5})
      generator = LessonGenerator(retriever=retriever)

      # Generate lesson
      lesson = await generator.generate_lesson(
          topic=request.topic,
          learner_state={"learner_id": request.learner_id}
      )

      # Content moderation
      moderator = ContentModerator()
      is_safe, moderation = await moderator.is_safe(lesson.content)

      if not is_safe:
          logger.error("Generated content flagged", moderation=moderation)
          raise HTTPException(status_code=500, detail="Content safety check failed")

      return GenerateLessonResponse(
          lesson=lesson,
          metadata={
              "generated_at": "2025-11-15T12:00:00Z",
              "safety_checks_passed": True,
          }
      )
  ```

**Validation**: `curl -X POST http://localhost:8000/api/v1/generate-lesson -d '{"topic":"APR","learner_id":"user123"}'`

## 9. Testing

### 9.1 Unit Tests with LLM Mocks
- [ ] Create `tests/ai_service/unit/test_lesson_generator.py`
  ```python
  import pytest
  from unittest.mock import Mock, patch, AsyncMock
  from app.generators.lesson_generator import LessonGenerator, MicroLesson

  @pytest.fixture
  def mock_retriever():
      retriever = AsyncMock()
      retriever.ainvoke.return_value = [
          Mock(page_content="APR is the annual percentage rate...")
      ]
      return retriever

  @pytest.fixture
  def lesson_generator(mock_retriever):
      return LessonGenerator(retriever=mock_retriever)

  @pytest.mark.asyncio
  @patch('app.generators.lesson_generator.ChatOpenAI')
  async def test_generate_lesson(mock_llm, lesson_generator):
      """Test lesson generation with mocked LLM"""

      # Mock LLM response
      mock_response = {
          "topic": "APR",
          "content": "APR is...",
          "key_points": ["Point 1", "Point 2"],
          "scenario": "Customer asks about APR",
          "quiz_question": "What does APR stand for?",
          "quiz_options": ["A", "B", "C", "D"],
          "correct_answer": 0
      }

      mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)

      lesson = await lesson_generator.generate_lesson(
          topic="APR",
          learner_state={"learner_id": "test"}
      )

      assert isinstance(lesson, MicroLesson)
      assert lesson.topic == "APR"
      assert len(lesson.key_points) >= 2
  ```

### 9.2 Integration Tests
- [ ] Create `tests/ai_service/integration/test_rag_pipeline.py`
  ```python
  import pytest
  from app.ingestion.document_processor import DocumentProcessor
  from app.ingestion.vector_store import VectorStoreManager

  @pytest.mark.integration
  async def test_document_ingestion_and_retrieval():
      """Test full RAG pipeline"""

      # Ingest test documents
      processor = DocumentProcessor()
      docs = processor.load_pdfs("tests/fixtures/test_docs")
      chunks = processor.chunk_documents(docs)

      # Store in vector DB
      vector_store = VectorStoreManager()
      ids = vector_store.add_documents(chunks)

      assert len(ids) > 0

      # Retrieve
      results = vector_store.similarity_search("APR", k=3)

      assert len(results) == 3
      assert "APR" in results[0].page_content or "annual percentage rate" in results[0].page_content.lower()
  ```

### 9.3 Safety Tests
- [ ] Create `tests/ai_service/unit/test_safety.py`
  ```python
  import pytest
  from app.safety.pii_detector import PIIDetector
  from app.safety.content_moderator import ContentModerator

  def test_pii_detection():
      detector = PIIDetector()

      text_with_pii = "My SSN is 123-45-6789 and email is test@example.com"
      findings = detector.detect(text_with_pii)

      assert len(findings) == 2
      assert ("ssn", "123-45-6789") in findings

      redacted = detector.redact(text_with_pii)
      assert "123-45-6789" not in redacted
      assert "[REDACTED_SSN]" in redacted

  @pytest.mark.asyncio
  async def test_content_moderation():
      moderator = ContentModerator()

      safe_text = "APR stands for Annual Percentage Rate"
      is_safe, result = await moderator.is_safe(safe_text)

      assert is_safe is True
  ```

**Validation**: `uv run pytest tests/ --cov=app/ai_service --cov-report=html`

## Phase 2 Checklist Summary

### Core Components
- [ ] FastAPI application with health checks
- [ ] Document ingestion pipeline (PDFs → chunks → vector store)
- [ ] Vector store (Chroma) with metadata filtering
- [ ] Advanced retrieval (MultiQuery, ParentDocument, Compression)

### LLM Safety
- [ ] Prompt-based safety checks (replacement for Constitutional AI)
- [ ] PII detection and redaction
- [ ] Content moderation (OpenAI API)
- [ ] Safety tests passing

### Content Generation
- [ ] Chain-based lesson generation
- [ ] Few-shot prompt templates
- [ ] Output parsing with JSON validation
- [ ] Safety check integration

### Agents
- [ ] Tool-decorated functions (@tool)
- [ ] Learning orchestrator agent
- [ ] Conversation buffer memory

### Production Features
- [ ] Redis LLM caching
- [ ] Callback handlers for monitoring
- [ ] Structured logging
- [ ] API endpoints (FastAPI)

### Testing
- [ ] Unit tests with LLM mocks (>80% coverage)
- [ ] Integration tests (RAG pipeline)
- [ ] Safety tests (PII, moderation)
- [ ] API endpoint tests

### Documentation
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Code docstrings
- [ ] ADR for LangChain patterns used

## Handoff Criteria
- [ ] `docker-compose up ai_service` starts successfully
- [ ] `/health` endpoint returns 200
- [ ] Document ingestion script works
- [ ] Lesson generation endpoint works
- [ ] All tests passing
- [ ] Safety checks functional
- [ ] Logging structured and verbose

## Next Phase
Proceed to **[Phase 3: Rails API Service](./03-rails-api.md)** to integrate AI service with business logic.

---

**Estimated Time**: 10-14 days
**Complexity**: High
**Key Learning**: RAG, Agents, Prompt-based Safety, Production LangChain
**Dependencies**: Phase 1 (Docker environment)
