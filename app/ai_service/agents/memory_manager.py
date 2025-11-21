from app.config.settings import settings
import redis
import json
import structlog
from typing import Dict, Any, List

logger = structlog.get_logger()

class LearningMemoryManager:
    """Manages learner conversation history and progress using Redis."""

    def __init__(self):
        """Initialize memory manager with Redis connection."""
        self.redis_url = settings.redis_url
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)

    async def get_learner_context(self, learner_id: str) -> Dict[str, Any]:
        """
        Retrieve learner's history and state.
        
        Args:
            learner_id: Unique learner identifier
            
        Returns:
            Dictionary containing learner context
        """
        key = f"learner:{learner_id}:context"
        context_json = self.redis_client.get(key)
        
        if context_json:
            try:
                return json.loads(context_json)
            except json.JSONDecodeError:
                logger.error("Failed to decode learner context", learner_id=learner_id)
        
        # Default context if not found
        return {
            "learner_id": learner_id,
            "topics_covered": [],
            "current_level": "beginner",
            "performance_metrics": {
                "average_score": 0.0,
                "quizzes_taken": 0
            },
            "preferences": {
                "difficulty": "medium"
            },
            "recent_interactions": []
        }

    async def update_learner_progress(self, learner_id: str, interaction: Dict[str, Any]):
        """
        Update learner's progress and history.
        
        Args:
            learner_id: Unique learner identifier
            interaction: Interaction data to store
        """
        context = await self.get_learner_context(learner_id)
        
        # Update recent interactions (keep last 10)
        context["recent_interactions"].append(interaction)
        if len(context["recent_interactions"]) > 10:
            context["recent_interactions"] = context["recent_interactions"][-10:]
            
        # Update topics if applicable
        if "topic" in interaction:
            if interaction["topic"] not in context["topics_covered"]:
                context["topics_covered"].append(interaction["topic"])
                
        # Update performance if quiz
        if interaction.get("type") == "quiz" and "score" in interaction:
            current_avg = context["performance_metrics"]["average_score"]
            count = context["performance_metrics"]["quizzes_taken"]
            new_score = interaction["score"]
            
            new_avg = ((current_avg * count) + new_score) / (count + 1)
            context["performance_metrics"]["average_score"] = new_avg
            context["performance_metrics"]["quizzes_taken"] += 1
            
        # Save back to Redis
        key = f"learner:{learner_id}:context"
        self.redis_client.set(key, json.dumps(context))
        
        logger.info("Updated learner progress", learner_id=learner_id)
