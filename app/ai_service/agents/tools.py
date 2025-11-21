from langchain_core.tools import tool
from pydantic import BaseModel, Field
import structlog
from typing import List, Optional, Dict, Any

from app.generators.lesson_generator import LessonGenerator
from app.ingestion.vector_store import VectorStoreManager

logger = structlog.get_logger()

# Input Schemas
class AssessKnowledgeInput(BaseModel):
    learner_id: str = Field(description="Unique learner identifier")
    topic: str = Field(description="Topic to assess")

class GenerateLessonInput(BaseModel):
    topic: str = Field(description="Topic for lesson")
    difficulty: str = Field(description="Difficulty level: easy, medium, or hard")
    learner_context: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Context about learner's past performance and preferences"
    )

class CreateScenarioInput(BaseModel):
    topic: str = Field(description="Topic to create scenario for")
    industry_context: str = Field(description="Industry context (e.g., retail, manufacturing, tech)")
    difficulty: str = Field(description="Difficulty level: easy, medium, or hard")

class EvaluateQuizInput(BaseModel):
    response: str = Field(description="Learner's answer")
    expected_answer: str = Field(description="The correct answer")
    topic: str = Field(description="Topic of the quiz")

class LearningPathInput(BaseModel):
    learner_id: str = Field(description="Unique learner identifier")
    current_topic: str = Field(description="Current topic being learned")
    performance: float = Field(description="Performance score (0.0 to 1.0)")

class TrackEngagementInput(BaseModel):
    learner_id: str = Field(description="Unique learner identifier")
    interaction_type: str = Field(description="Type of interaction (chat, quiz, lesson)")
    duration: int = Field(description="Duration of interaction in seconds")

# Tools
@tool(args_schema=AssessKnowledgeInput)
def assess_knowledge(learner_id: str, topic: str) -> dict:
    """Assess learner's current knowledge on a topic based on history."""
    # In a real app, this would query the database/analytics service
    # For now, we mock it based on the learner_id to allow testing different states
    logger.info("Assessing knowledge", learner_id=learner_id, topic=topic)
    
    # Mock logic for demonstration
    if "novice" in learner_id:
        return {
            "score": 0.2,
            "level": "beginner",
            "weak_areas": ["basic concepts", "terminology"],
            "strong_areas": []
        }
    elif "expert" in learner_id:
        return {
            "score": 0.9,
            "level": "advanced",
            "weak_areas": [],
            "strong_areas": ["basic concepts", "advanced application", "strategy"]
        }
    else:
        return {
            "score": 0.5,
            "level": "intermediate",
            "weak_areas": ["complex scenarios"],
            "strong_areas": ["basic concepts"]
        }

@tool(args_schema=GenerateLessonInput)
def generate_adaptive_lesson(topic: str, difficulty: str, learner_context: dict = None) -> dict:
    """Generate a personalized lesson based on learner state and difficulty."""
    logger.info("Generating adaptive lesson", topic=topic, difficulty=difficulty)
    
    try:
        # Initialize RAG components
        vector_store_manager = VectorStoreManager()
        try:
            vector_store = vector_store_manager.load_vector_store()
            retriever = vector_store_manager.as_retriever(vector_store)
        except Exception:
            logger.warning("Vector store not available, generating without RAG")
            retriever = None

        # Initialize generator
        generator = LessonGenerator(retriever=retriever)
        
        # Generate base lesson
        lesson = generator.generate_lesson(topic=topic, learner_id=learner_context.get("learner_id") if learner_context else None)
        
        # Add metadata about adaptation
        lesson["adaptation"] = {
            "difficulty": difficulty,
            "customized_for": learner_context.get("learner_id") if learner_context else "general"
        }
        
        return lesson
        
    except Exception as e:
        logger.error("Failed to generate lesson", error=str(e))
        return {
            "error": "Failed to generate lesson",
            "details": str(e)
        }

@tool(args_schema=CreateScenarioInput)
def create_practice_scenario(topic: str, industry_context: str, difficulty: str) -> str:
    """Create a realistic work scenario for practice."""
    logger.info("Creating practice scenario", topic=topic, context=industry_context)
    
    # This would ideally call an LLM, but for the tool definition we can return a structured prompt
    # or call the LLM directly. Since we are inside an agent that has an LLM, 
    # we could just return the prompt, but tools usually do the work.
    # Let's simulate a scenario generation or use a simple template for now 
    # to avoid circular dependencies if we were to use the agent's LLM here.
    # In a full implementation, this would use a specialized chain.
    
    return f"""
    Scenario: You are working with a client in the {industry_context} industry.
    They are asking about {topic}. 
    
    Situation: The client is hesitant because they don't understand how {topic} applies to their business cycle.
    
    Task: Explain {topic} using an example relevant to {industry_context}.
    
    Difficulty: {difficulty}
    """

@tool(args_schema=EvaluateQuizInput)
def evaluate_quiz_response(response: str, expected_answer: str, topic: str) -> dict:
    """Evaluate learner response with feedback."""
    logger.info("Evaluating quiz response", topic=topic)
    
    # Simple matching for now, but could be semantic comparison using LLM
    is_correct = response.lower().strip() == expected_answer.lower().strip()
    
    return {
        "correct": is_correct,
        "feedback": "Correct! Well done." if is_correct else f"Not quite. The correct answer was: {expected_answer}",
        "confidence_score": 1.0 if is_correct else 0.0,
        "next_recommendation": "advance to next topic" if is_correct else "review current topic"
    }

@tool(args_schema=LearningPathInput)
def get_learning_path(learner_id: str, current_topic: str, performance: float) -> dict:
    """Determine next topics based on performance."""
    logger.info("Determining learning path", learner_id=learner_id, performance=performance)
    
    if performance > 0.8:
        return {
            "next_topic": "Advanced " + current_topic,
            "difficulty_adjustment": "increase",
            "reinforcement_needed": False
        }
    elif performance < 0.5:
        return {
            "next_topic": current_topic,
            "difficulty_adjustment": "decrease",
            "reinforcement_needed": True
        }
    else:
        return {
            "next_topic": "Related concepts to " + current_topic,
            "difficulty_adjustment": "maintain",
            "reinforcement_needed": False
        }

@tool(args_schema=TrackEngagementInput)
def track_engagement(learner_id: str, interaction_type: str, duration: int) -> dict:
    """Track learner engagement metrics."""
    logger.info("Tracking engagement", learner_id=learner_id, type=interaction_type)
    
    # Mock saving to DB
    score = min(1.0, duration / 300) # Cap at 5 minutes
    
    return {
        "status": "recorded",
        "engagement_score": score
    }

# Export list of tools
AGENT_TOOLS = [
    assess_knowledge,
    generate_adaptive_lesson,
    create_practice_scenario,
    evaluate_quiz_response,
    get_learning_path,
    track_engagement
]
