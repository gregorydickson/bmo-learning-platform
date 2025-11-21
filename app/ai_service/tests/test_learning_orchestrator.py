"""Tests for learning orchestrator agent."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from agents.learning_orchestrator import LearningOrchestrator


class TestLearningOrchestrator:
    """Test suite for LearningOrchestrator."""

    @pytest.fixture
    def mock_memory_manager(self):
        """Mock memory manager."""
        with patch("agents.learning_orchestrator.LearningMemoryManager") as mock:
            manager = MagicMock()
            
            # Mock get_learner_context
            async def mock_get_context(learner_id):
                return {
                    "learner_id": learner_id,
                    "topics_covered": [],
                    "current_level": "beginner"
                }
            manager.get_learner_context = mock_get_context
            
            # Mock update_learner_progress
            async def mock_update_progress(learner_id, interaction):
                pass
            manager.update_learner_progress = mock_update_progress
            
            mock.return_value = manager
            yield mock

    @pytest.fixture
    def mock_agent_graph(self):
        """Mock agent graph."""
        with patch("agents.learning_orchestrator.create_agent") as mock:
            graph = MagicMock()
            
            # Mock astream
            async def mock_astream(inputs, stream_mode=None):
                # Simulate agent response
                message = MagicMock()
                message.content = "This is a test response from the agent."
                yield {"messages": [message]}
            
            graph.astream = mock_astream
            mock.return_value = graph
            yield mock

    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, mock_memory_manager):
        """Test orchestrator initializes correctly."""
        orchestrator = LearningOrchestrator()
        
        assert orchestrator.llm is not None
        assert orchestrator.tools is not None
        assert len(orchestrator.tools) > 0

    @pytest.mark.asyncio
    async def test_orchestrate_learning_session_success(self, mock_memory_manager, mock_agent_graph):
        """Test successful learning session orchestration."""
        orchestrator = LearningOrchestrator()
        
        result = await orchestrator.orchestrate_learning_session(
            learner_id="test_123",
            request="I want to learn about APR"
        )
        
        assert result["status"] == "success"
        assert "response" in result
        assert result["learner_id"] == "test_123"

    @pytest.mark.asyncio
    async def test_orchestrate_learning_session_error_handling(self, mock_memory_manager):
        """Test error handling in orchestration."""
        with patch("agents.learning_orchestrator.create_agent") as mock_create:
            # Make astream raise an exception
            graph = MagicMock()
            async def mock_astream_error(inputs, stream_mode=None):
                raise Exception("Test error")
                yield  # Make it a generator
            graph.astream = mock_astream_error
            mock_create.return_value = graph
            
            orchestrator = LearningOrchestrator()
            result = await orchestrator.orchestrate_learning_session(
                learner_id="test_123",
                request="Test request"
            )
            
            assert result["status"] == "error"
            assert "error" in result

    @pytest.mark.asyncio
    async def test_adaptive_lesson_flow(self, mock_memory_manager, mock_agent_graph):
        """Test adaptive lesson flow."""
        orchestrator = LearningOrchestrator()
        
        result = await orchestrator.adaptive_lesson_flow(
            learner_id="test_123",
            topic="APR"
        )
        
        assert "response" in result
        assert result["learner_id"] == "test_123"
