"""API routes for agent interactions."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import structlog

from agents.learning_orchestrator import LearningOrchestrator

router = APIRouter()
logger = structlog.get_logger()

# Request/Response Models
class AgentChatRequest(BaseModel):
    """Request for agent chat interaction."""
    learner_id: str = Field(..., description="Unique learner identifier")
    message: str = Field(..., description="User's message to the agent")

class AgentChatResponse(BaseModel):
    """Response from agent chat."""
    response: str = Field(..., description="Agent's response")
    learner_id: str
    status: str

class StartLessonRequest(BaseModel):
    """Request to start a personalized lesson."""
    learner_id: str = Field(..., description="Unique learner identifier")
    topic: str = Field(..., description="Topic to learn")

class AdaptiveLessonResponse(BaseModel):
    """Response containing adaptive lesson."""
    response: str = Field(..., description="Lesson content and guidance")
    learner_id: str
    status: str

class QuizAnswerRequest(BaseModel):
    """Request to submit a quiz answer."""
    learner_id: str = Field(..., description="Unique learner identifier")
    topic: str = Field(..., description="Topic of the quiz")
    question: str = Field(..., description="The quiz question")
    answer: str = Field(..., description="Learner's answer")
    expected_answer: str = Field(..., description="Correct answer")

class FeedbackResponse(BaseModel):
    """Response with quiz feedback."""
    response: str = Field(..., description="Feedback and next steps")
    learner_id: str
    status: str

class LearningPathResponse(BaseModel):
    """Response with personalized learning path."""
    response: str = Field(..., description="Learning path recommendations")
    learner_id: str
    status: str


@router.post("/agent/chat", response_model=AgentChatResponse)
async def agent_chat(request: AgentChatRequest) -> AgentChatResponse:
    """
    Interactive chat with learning agent.
    
    The agent will:
    - Understand the learner's intent
    - Access their learning history
    - Provide personalized guidance
    - Use tools as needed (assess, generate lessons, etc.)
    """
    logger.info("Agent chat requested", learner_id=request.learner_id)
    
    try:
        orchestrator = LearningOrchestrator()
        result = await orchestrator.orchestrate_learning_session(
            learner_id=request.learner_id,
            request=request.message
        )
        
        return AgentChatResponse(**result)
        
    except Exception as e:
        logger.error("Agent chat failed", error=str(e), learner_id=request.learner_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/start-lesson", response_model=AdaptiveLessonResponse)
async def start_adaptive_lesson(request: StartLessonRequest) -> AdaptiveLessonResponse:
    """
    Start a personalized lesson on a topic.
    
    The agent will:
    1. Assess the learner's current knowledge
    2. Determine appropriate difficulty level
    3. Generate customized lesson content
    4. Create practice scenarios
    5. Prepare assessment questions
    """
    logger.info("Adaptive lesson requested", learner_id=request.learner_id, topic=request.topic)
    
    try:
        orchestrator = LearningOrchestrator()
        result = await orchestrator.adaptive_lesson_flow(
            learner_id=request.learner_id,
            topic=request.topic
        )
        
        return AdaptiveLessonResponse(**result)
        
    except Exception as e:
        logger.error("Lesson start failed", error=str(e), learner_id=request.learner_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/submit-answer", response_model=FeedbackResponse)
async def submit_quiz_answer(request: QuizAnswerRequest) -> FeedbackResponse:
    """
    Process quiz answer with personalized feedback.
    
    The agent will:
    1. Evaluate the answer
    2. Provide constructive feedback
    3. Recommend next steps based on performance
    """
    logger.info("Quiz answer submitted", learner_id=request.learner_id, topic=request.topic)
    
    try:
        orchestrator = LearningOrchestrator()
        
        # Construct a message for the agent
        message = f"""I just answered a quiz question about {request.topic}.
        
Question: {request.question}
My answer: {request.answer}
Correct answer: {request.expected_answer}

Please evaluate my response and provide feedback."""
        
        result = await orchestrator.orchestrate_learning_session(
            learner_id=request.learner_id,
            request=message
        )
        
        return FeedbackResponse(**result)
        
    except Exception as e:
        logger.error("Answer submission failed", error=str(e), learner_id=request.learner_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/learning-path/{learner_id}", response_model=LearningPathResponse)
async def get_personalized_path(learner_id: str) -> LearningPathResponse:
    """
    Get personalized learning path recommendations.
    
    The agent will:
    1. Analyze the learner's progress
    2. Identify knowledge gaps
    3. Recommend next topics in optimal sequence
    """
    logger.info("Learning path requested", learner_id=learner_id)
    
    try:
        orchestrator = LearningOrchestrator()
        
        message = "Based on my learning history and performance, what should I learn next?"
        
        result = await orchestrator.orchestrate_learning_session(
            learner_id=learner_id,
            request=message
        )
        
        return LearningPathResponse(**result)
        
    except Exception as e:
        logger.error("Learning path generation failed", error=str(e), learner_id=learner_id)
        raise HTTPException(status_code=500, detail=str(e))
