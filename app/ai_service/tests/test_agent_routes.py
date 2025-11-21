"""Tests for agent API routes."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app


class TestAgentRoutes:
    """Test suite for agent API routes."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_orchestrator(self):
        """Mock LearningOrchestrator."""
        with patch("app.api.agent_routes.LearningOrchestrator") as mock:
            orchestrator = MagicMock()
            
            # Mock orchestrate_learning_session
            async def mock_orchestrate(learner_id, request):
                return {
                    "response": "Test response from agent",
                    "learner_id": learner_id,
                    "status": "success"
                }
            orchestrator.orchestrate_learning_session = mock_orchestrate
            
            # Mock adaptive_lesson_flow
            async def mock_lesson_flow(learner_id, topic):
                return {
                    "response": f"Lesson about {topic}",
                    "learner_id": learner_id,
                    "status": "success"
                }
            orchestrator.adaptive_lesson_flow = mock_lesson_flow
            
            mock.return_value = orchestrator
            yield mock

    def test_agent_chat_success(self, client, mock_orchestrator):
        """Test successful agent chat."""
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "learner_id": "test_123",
                "message": "I want to learn about APR"
            },
            headers={"X-API-Key": "dev_key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["learner_id"] == "test_123"
        assert "response" in data

    def test_agent_chat_missing_fields(self, client):
        """Test agent chat with missing required fields."""
        response = client.post(
            "/api/v1/agent/chat",
            json={"learner_id": "test_123"},  # Missing message
            headers={"X-API-Key": "dev_key"}
        )
        
        assert response.status_code == 422  # Validation error

    def test_agent_chat_unauthorized(self, client):
        """Test agent chat without API key."""
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "learner_id": "test_123",
                "message": "Test message"
            }
        )
        
        assert response.status_code == 403  # Forbidden

    def test_start_adaptive_lesson_success(self, client, mock_orchestrator):
        """Test starting an adaptive lesson."""
        response = client.post(
            "/api/v1/agent/start-lesson",
            json={
                "learner_id": "test_123",
                "topic": "APR"
            },
            headers={"X-API-Key": "dev_key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "APR" in data["response"]

    def test_start_adaptive_lesson_missing_topic(self, client):
        """Test starting lesson without topic."""
        response = client.post(
            "/api/v1/agent/start-lesson",
            json={"learner_id": "test_123"},
            headers={"X-API-Key": "dev_key"}
        )
        
        assert response.status_code == 422

    def test_submit_quiz_answer_success(self, client, mock_orchestrator):
        """Test submitting a quiz answer."""
        response = client.post(
            "/api/v1/agent/submit-answer",
            json={
                "learner_id": "test_123",
                "topic": "APR",
                "question": "What is APR?",
                "answer": "B",
                "expected_answer": "B"
            },
            headers={"X-API-Key": "dev_key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_submit_quiz_answer_validation(self, client):
        """Test quiz answer submission with missing fields."""
        response = client.post(
            "/api/v1/agent/submit-answer",
            json={
                "learner_id": "test_123",
                "topic": "APR"
                # Missing question, answer, expected_answer
            },
            headers={"X-API-Key": "dev_key"}
        )
        
        assert response.status_code == 422

    def test_get_learning_path_success(self, client, mock_orchestrator):
        """Test getting personalized learning path."""
        response = client.get(
            "/api/v1/agent/learning-path/test_123",
            headers={"X-API-Key": "dev_key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["learner_id"] == "test_123"

    def test_get_learning_path_unauthorized(self, client):
        """Test learning path without authentication."""
        response = client.get("/api/v1/agent/learning-path/test_123")
        
        assert response.status_code == 403

    def test_agent_chat_error_handling(self, client):
        """Test error handling when orchestrator fails."""
        with patch("app.api.agent_routes.LearningOrchestrator") as mock:
            orchestrator = MagicMock()
            
            async def mock_error(learner_id, request):
                raise Exception("Test error")
            
            orchestrator.orchestrate_learning_session = mock_error
            mock.return_value = orchestrator
            
            response = client.post(
                "/api/v1/agent/chat",
                json={
                    "learner_id": "test_123",
                    "message": "Test"
                },
                headers={"X-API-Key": "dev_key"}
            )
            
            assert response.status_code == 500

    def test_start_lesson_error_handling(self, client):
        """Test error handling when lesson generation fails."""
        with patch("app.api.agent_routes.LearningOrchestrator") as mock:
            orchestrator = MagicMock()
            
            async def mock_error(learner_id, topic):
                raise ValueError("Invalid topic")
            
            orchestrator.adaptive_lesson_flow = mock_error
            mock.return_value = orchestrator
            
            response = client.post(
                "/api/v1/agent/start-lesson",
                json={
                    "learner_id": "test_123",
                    "topic": "InvalidTopic"
                },
                headers={"X-API-Key": "dev_key"}
            )
            
            assert response.status_code == 500


class TestAgentRouteIntegration:
    """Integration tests for agent routes."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_agent_routes_registered(self, client):
        """Test that agent routes are properly registered."""
        # Test that the routes exist by checking OPTIONS
        response = client.options("/api/v1/agent/chat")
        assert response.status_code in [200, 405]  # Either allowed or method not allowed

    def test_api_documentation_includes_agent_routes(self, client):
        """Test that agent routes appear in OpenAPI docs."""
        response = client.get("/docs")
        assert response.status_code == 200
        
        # Check OpenAPI schema
        openapi_response = client.get("/openapi.json")
        assert openapi_response.status_code == 200
        
        schema = openapi_response.json()
        paths = schema.get("paths", {})
        
        # Verify agent endpoints are documented
        assert "/api/v1/agent/chat" in paths
        assert "/api/v1/agent/start-lesson" in paths
        assert "/api/v1/agent/submit-answer" in paths
        assert "/api/v1/agent/learning-path/{learner_id}" in paths
