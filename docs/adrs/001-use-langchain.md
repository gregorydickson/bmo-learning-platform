# ADR-001: Use LangChain for AI Orchestration

**Date**: 2025-11-15
**Status**: Accepted

## Context
We need an AI framework for RAG, agents, and content generation to build a production-ready microlearning platform. The framework must support:
- Document ingestion and retrieval (RAG)
- Agent-based workflows
- Content generation chains
- LLM safety guardrails
- Production monitoring and observability

## Decision
Use LangChain 1.0.7 as the primary AI orchestration framework for the BMO Learning Platform.

## Consequences

**Positive**:
- Rich ecosystem of tools and integrations with OpenAI, ChromaDB, and other services
- Active community with extensive documentation and examples
- Constitutional AI for implementing safety guardrails in financial services context
- Built-in support for RAG patterns, agents, chains, and memory
- Production-ready features: callbacks, monitoring, caching
- Strong typing support with Pydantic v2

**Negative**:
- Abstraction complexity can obscure underlying LLM interactions
- Rapid version changes require careful dependency management
- Learning curve for team members unfamiliar with LangChain patterns
- Performance overhead from abstraction layers
- Debugging can be challenging due to multiple layers

## Alternatives Considered

**Haystack**:
- Pros: Clean API, good for pure RAG
- Cons: Less mature agent framework, smaller ecosystem
- Why rejected: Weaker agent capabilities needed for adaptive learning

**LlamaIndex**:
- Pros: Excellent for document indexing and retrieval
- Cons: Limited agent framework, focused primarily on RAG
- Why rejected: Insufficient support for complex multi-agent workflows

**Custom Implementation**:
- Pros: Full control, minimal dependencies, optimized for specific use case
- Cons: Significant development time, maintenance burden, reinventing the wheel
- Why rejected: Timeline constraints and desire to demonstrate best practices
