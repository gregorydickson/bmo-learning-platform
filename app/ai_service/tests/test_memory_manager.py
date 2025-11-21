"""Tests for learning memory manager."""
import pytest
from unittest.mock import MagicMock, patch
from agents.memory_manager import LearningMemoryManager
import json


class TestLearningMemoryManager:
    """Test suite for LearningMemoryManager."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        with patch("agents.memory_manager.redis") as mock:
            client = MagicMock()
            mock.from_url.return_value = client
            yield client

    def test_initialization(self, mock_redis):
        """Test memory manager initializes correctly."""
        manager = LearningMemoryManager()
        
        assert manager.redis_client is not None
        assert manager.redis_url is not None

    @pytest.mark.asyncio
    async def test_get_learner_context_existing(self, mock_redis):
        """Test retrieving existing learner context."""
        # Mock existing context
        existing_context = {
            "learner_id": "test_123",
            "topics_covered": ["APR", "Interest Rates"],
            "current_level": "intermediate",
            "performance_metrics": {
                "average_score": 0.75,
                "quizzes_taken": 5
            }
        }
        mock_redis.get.return_value = json.dumps(existing_context)
        
        manager = LearningMemoryManager()
        context = await manager.get_learner_context("test_123")
        
        assert context["learner_id"] == "test_123"
        assert len(context["topics_covered"]) == 2
        assert context["performance_metrics"]["average_score"] == 0.75
        mock_redis.get.assert_called_once_with("learner:test_123:context")

    @pytest.mark.asyncio
    async def test_get_learner_context_new_learner(self, mock_redis):
        """Test retrieving context for new learner."""
        mock_redis.get.return_value = None
        
        manager = LearningMemoryManager()
        context = await manager.get_learner_context("new_learner")
        
        assert context["learner_id"] == "new_learner"
        assert context["topics_covered"] == []
        assert context["current_level"] == "beginner"
        assert context["performance_metrics"]["average_score"] == 0.0

    @pytest.mark.asyncio
    async def test_get_learner_context_invalid_json(self, mock_redis):
        """Test handling of corrupted context data."""
        mock_redis.get.return_value = "invalid json {"
        
        manager = LearningMemoryManager()
        context = await manager.get_learner_context("test_123")
        
        # Should return default context
        assert context["learner_id"] == "test_123"
        assert context["topics_covered"] == []

    @pytest.mark.asyncio
    async def test_update_learner_progress_new_topic(self, mock_redis):
        """Test updating progress with new topic."""
        # Mock existing context
        existing_context = {
            "learner_id": "test_123",
            "topics_covered": ["APR"],
            "current_level": "beginner",
            "performance_metrics": {
                "average_score": 0.0,
                "quizzes_taken": 0
            },
            "preferences": {"difficulty": "medium"},
            "recent_interactions": []
        }
        mock_redis.get.return_value = json.dumps(existing_context)
        
        manager = LearningMemoryManager()
        interaction = {
            "type": "lesson",
            "topic": "Interest Rates",
            "timestamp": "2025-11-19T12:00:00Z"
        }
        
        await manager.update_learner_progress("test_123", interaction)
        
        # Verify Redis set was called
        assert mock_redis.set.called
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "learner:test_123:context"
        
        # Verify updated context
        updated_context = json.loads(call_args[0][1])
        assert "Interest Rates" in updated_context["topics_covered"]
        assert len(updated_context["recent_interactions"]) == 1

    @pytest.mark.asyncio
    async def test_update_learner_progress_quiz_score(self, mock_redis):
        """Test updating progress with quiz score."""
        existing_context = {
            "learner_id": "test_123",
            "topics_covered": ["APR"],
            "current_level": "beginner",
            "performance_metrics": {
                "average_score": 0.6,
                "quizzes_taken": 2
            },
            "preferences": {"difficulty": "medium"},
            "recent_interactions": []
        }
        mock_redis.get.return_value = json.dumps(existing_context)
        
        manager = LearningMemoryManager()
        interaction = {
            "type": "quiz",
            "topic": "APR",
            "score": 0.9
        }
        
        await manager.update_learner_progress("test_123", interaction)
        
        # Verify score calculation
        call_args = mock_redis.set.call_args
        updated_context = json.loads(call_args[0][1])
        
        # New average: (0.6 * 2 + 0.9) / 3 = 0.7
        assert abs(updated_context["performance_metrics"]["average_score"] - 0.7) < 0.001
        assert updated_context["performance_metrics"]["quizzes_taken"] == 3

    @pytest.mark.asyncio
    async def test_update_learner_progress_interaction_limit(self, mock_redis):
        """Test that recent interactions are limited to 10."""
        existing_interactions = [{"id": i} for i in range(10)]
        existing_context = {
            "learner_id": "test_123",
            "topics_covered": [],
            "current_level": "beginner",
            "performance_metrics": {
                "average_score": 0.0,
                "quizzes_taken": 0
            },
            "preferences": {"difficulty": "medium"},
            "recent_interactions": existing_interactions
        }
        mock_redis.get.return_value = json.dumps(existing_context)
        
        manager = LearningMemoryManager()
        new_interaction = {"id": 11, "type": "lesson"}
        
        await manager.update_learner_progress("test_123", new_interaction)
        
        call_args = mock_redis.set.call_args
        updated_context = json.loads(call_args[0][1])
        
        # Should keep only last 10
        assert len(updated_context["recent_interactions"]) == 10
        assert updated_context["recent_interactions"][-1]["id"] == 11
        # First interaction should be id=1 (0-indexed list, removed id=0)
        assert updated_context["recent_interactions"][0]["id"] == 1

    @pytest.mark.asyncio
    async def test_update_learner_progress_duplicate_topic(self, mock_redis):
        """Test that duplicate topics are not added."""
        existing_context = {
            "learner_id": "test_123",
            "topics_covered": ["APR", "Interest Rates"],
            "current_level": "intermediate",
            "performance_metrics": {
                "average_score": 0.0,
                "quizzes_taken": 0
            },
            "preferences": {"difficulty": "medium"},
            "recent_interactions": []
        }
        mock_redis.get.return_value = json.dumps(existing_context)
        
        manager = LearningMemoryManager()
        interaction = {
            "type": "lesson",
            "topic": "APR"  # Already in topics_covered
        }
        
        await manager.update_learner_progress("test_123", interaction)
        
        call_args = mock_redis.set.call_args
        updated_context = json.loads(call_args[0][1])
        
        # Should still have only 2 topics
        assert len(updated_context["topics_covered"]) == 2
        assert updated_context["topics_covered"].count("APR") == 1
