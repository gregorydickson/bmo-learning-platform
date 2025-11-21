"""Tests for agent tools."""
import pytest
from unittest.mock import MagicMock, patch
from agents.tools import (
    assess_knowledge,
    generate_adaptive_lesson,
    create_practice_scenario,
    evaluate_quiz_response,
    get_learning_path,
    track_engagement
)


class TestAgentTools:
    """Test suite for agent tools."""

    def test_assess_knowledge_novice(self):
        """Test knowledge assessment for novice learner."""
        result = assess_knowledge.invoke({"learner_id": "novice_123", "topic": "APR"})
        
        assert result["score"] == 0.2
        assert result["level"] == "beginner"
        assert len(result["weak_areas"]) > 0

    def test_assess_knowledge_expert(self):
        """Test knowledge assessment for expert learner."""
        result = assess_knowledge.invoke({"learner_id": "expert_456", "topic": "APR"})
        
        assert result["score"] == 0.9
        assert result["level"] == "advanced"
        assert len(result["strong_areas"]) > 0

    def test_assess_knowledge_intermediate(self):
        """Test knowledge assessment for intermediate learner."""
        result = assess_knowledge.invoke({"learner_id": "learner_789", "topic": "APR"})
        
        assert result["score"] == 0.5
        assert result["level"] == "intermediate"

    @patch("agents.tools.VectorStoreManager")
    @patch("agents.tools.LessonGenerator")
    def test_generate_adaptive_lesson_success(self, mock_generator_class, mock_vector_store):
        """Test adaptive lesson generation."""
        # Mock the generator
        mock_generator = MagicMock()
        mock_generator.generate_lesson.return_value = {
            "topic": "APR",
            "content": "Test content",
            "key_points": ["Point 1", "Point 2"],
            "scenario": "Test scenario",
            "quiz_question": "What is APR?",
            "quiz_options": ["A", "B", "C", "D"],
            "correct_answer": 1
        }
        mock_generator_class.return_value = mock_generator
        
        result = generate_adaptive_lesson.invoke({
            "topic": "APR",
            "difficulty": "easy",
            "learner_context": {"learner_id": "test_123"}
        })
        
        assert "topic" in result
        assert result["topic"] == "APR"
        assert "adaptation" in result
        assert result["adaptation"]["difficulty"] == "easy"

    def test_create_practice_scenario(self):
        """Test practice scenario creation."""
        result = create_practice_scenario.invoke({
            "topic": "APR",
            "industry_context": "retail",
            "difficulty": "medium"
        })
        
        assert isinstance(result, str)
        assert "APR" in result
        assert "retail" in result
        assert "medium" in result

    def test_evaluate_quiz_response_correct(self):
        """Test quiz evaluation with correct answer."""
        result = evaluate_quiz_response.invoke({
            "response": "B",
            "expected_answer": "B",
            "topic": "APR"
        })
        
        assert result["correct"] is True
        assert "Correct" in result["feedback"]
        assert result["next_recommendation"] == "advance to next topic"

    def test_evaluate_quiz_response_incorrect(self):
        """Test quiz evaluation with incorrect answer."""
        result = evaluate_quiz_response.invoke({
            "response": "A",
            "expected_answer": "B",
            "topic": "APR"
        })
        
        assert result["correct"] is False
        assert "correct answer" in result["feedback"].lower()
        assert result["next_recommendation"] == "review current topic"

    def test_get_learning_path_high_performance(self):
        """Test learning path for high performer."""
        result = get_learning_path.invoke({
            "learner_id": "test_123",
            "current_topic": "APR",
            "performance": 0.9
        })
        
        assert result["difficulty_adjustment"] == "increase"
        assert result["reinforcement_needed"] is False
        assert "Advanced" in result["next_topic"]

    def test_get_learning_path_low_performance(self):
        """Test learning path for struggling learner."""
        result = get_learning_path.invoke({
            "learner_id": "test_123",
            "current_topic": "APR",
            "performance": 0.3
        })
        
        assert result["difficulty_adjustment"] == "decrease"
        assert result["reinforcement_needed"] is True
        assert result["next_topic"] == "APR"

    def test_get_learning_path_medium_performance(self):
        """Test learning path for average performer."""
        result = get_learning_path.invoke({
            "learner_id": "test_123",
            "current_topic": "APR",
            "performance": 0.6
        })
        
        assert result["difficulty_adjustment"] == "maintain"
        assert result["reinforcement_needed"] is False

    def test_track_engagement(self):
        """Test engagement tracking."""
        result = track_engagement.invoke({
            "learner_id": "test_123",
            "interaction_type": "lesson",
            "duration": 180
        })
        
        assert result["status"] == "recorded"
        assert "engagement_score" in result
        assert 0 <= result["engagement_score"] <= 1.0


class TestAgentToolsEdgeCases:
    """Test edge cases and error handling for agent tools."""

    def test_assess_knowledge_different_topics(self):
        """Test assessment works with different topics."""
        topics = ["APR", "Interest Rates", "Credit Limits", "Rewards Programs"]
        
        for topic in topics:
            result = assess_knowledge.invoke({
                "learner_id": "test_123",
                "topic": topic
            })
            assert "score" in result
            assert "level" in result

    @patch("agents.tools.VectorStoreManager")
    @patch("agents.tools.LessonGenerator")
    def test_generate_adaptive_lesson_without_rag(self, mock_generator_class, mock_vector_store):
        """Test lesson generation when RAG is unavailable."""
        # Simulate RAG failure
        mock_vector_store.side_effect = Exception("Vector store unavailable")
        
        mock_generator = MagicMock()
        mock_generator.generate_lesson.return_value = {
            "topic": "APR",
            "content": "Basic content without RAG"
        }
        mock_generator_class.return_value = mock_generator
        
        result = generate_adaptive_lesson.invoke({
            "topic": "APR",
            "difficulty": "easy",
            "learner_context": None
        })
        
        # Should handle error gracefully
        assert "error" in result or "topic" in result

    @patch("agents.tools.VectorStoreManager")
    @patch("agents.tools.LessonGenerator")
    def test_generate_adaptive_lesson_error_handling(self, mock_generator_class, mock_vector_store):
        """Test error handling in lesson generation."""
        mock_generator = MagicMock()
        mock_generator.generate_lesson.side_effect = Exception("Generation failed")
        mock_generator_class.return_value = mock_generator
        
        result = generate_adaptive_lesson.invoke({
            "topic": "APR",
            "difficulty": "easy",
            "learner_context": {}
        })
        
        assert "error" in result

    def test_evaluate_quiz_response_case_insensitive(self):
        """Test quiz evaluation is case-insensitive."""
        result = evaluate_quiz_response.invoke({
            "response": "b",
            "expected_answer": "B",
            "topic": "APR"
        })
        
        assert result["correct"] is True

    def test_evaluate_quiz_response_whitespace_handling(self):
        """Test quiz evaluation handles whitespace."""
        result = evaluate_quiz_response.invoke({
            "response": "  B  ",
            "expected_answer": "B",
            "topic": "APR"
        })
        
        assert result["correct"] is True

    def test_get_learning_path_boundary_performance(self):
        """Test learning path at performance boundaries."""
        # Exactly at threshold
        result = get_learning_path.invoke({
            "learner_id": "test_123",
            "current_topic": "APR",
            "performance": 0.8
        })
        assert result["difficulty_adjustment"] in ["increase", "maintain"]
        
        # At lower boundary
        result = get_learning_path.invoke({
            "learner_id": "test_123",
            "current_topic": "APR",
            "performance": 0.5
        })
        assert result["difficulty_adjustment"] in ["decrease", "maintain"]

    def test_track_engagement_various_durations(self):
        """Test engagement tracking with various durations."""
        durations = [0, 60, 180, 300, 600]
        
        for duration in durations:
            result = track_engagement.invoke({
                "learner_id": "test_123",
                "interaction_type": "lesson",
                "duration": duration
            })
            
            assert result["status"] == "recorded"
            assert 0 <= result["engagement_score"] <= 1.0

    def test_track_engagement_different_types(self):
        """Test engagement tracking for different interaction types."""
        types = ["lesson", "quiz", "chat", "practice"]
        
        for interaction_type in types:
            result = track_engagement.invoke({
                "learner_id": "test_123",
                "interaction_type": interaction_type,
                "duration": 120
            })
            
            assert result["status"] == "recorded"

    def test_create_practice_scenario_various_industries(self):
        """Test scenario creation for different industries."""
        industries = ["retail", "manufacturing", "technology", "healthcare"]
        
        for industry in industries:
            result = create_practice_scenario.invoke({
                "topic": "APR",
                "industry_context": industry,
                "difficulty": "medium"
            })
            
            assert isinstance(result, str)
            assert industry in result

    def test_create_practice_scenario_difficulty_levels(self):
        """Test scenario creation at different difficulty levels."""
        difficulties = ["easy", "medium", "hard"]
        
        for difficulty in difficulties:
            result = create_practice_scenario.invoke({
                "topic": "Credit Limits",
                "industry_context": "retail",
                "difficulty": difficulty
            })
            
            assert isinstance(result, str)
            assert difficulty in result
