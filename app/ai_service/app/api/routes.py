"""API routes for AI service."""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional
import structlog

from app.generators.lesson_generator import LessonGenerator, LessonContent
from app.safety.safety_validator import SafetyValidator
from app.ingestion.vector_store import VectorStoreManager
from app.config.settings import settings

router = APIRouter()
logger = structlog.get_logger()

# Initialize components
vector_store_manager = VectorStoreManager()
safety_validator = SafetyValidator()


class LessonRequest(BaseModel):
    """Lesson generation request."""
    topic: str = Field(..., description="Lesson topic")
    learner_id: Optional[str] = Field(None, description="Learner ID for personalization")
    difficulty: str = Field("medium", description="Difficulty level")


class LessonResponse(BaseModel):
    """Lesson generation response."""
    lesson: dict
    metadata: dict
    safety_check: dict


@router.get("/status")
async def status():
    """Service status endpoint."""
    return {
        "service": "ai_service",
        "version": "0.1.0",
        "status": "operational",
        "features": {
            "rag": True,
            "lesson_generation": True,
            "safety_validation": True
        }
    }


@router.post("/generate-lesson", response_model=LessonResponse)
async def generate_lesson(request: LessonRequest):
    """
    Generate a microlearning lesson.

    Args:
        request: Lesson generation request

    Returns:
        Generated lesson with safety validation
    """
    logger.info("Lesson generation requested", topic=request.topic)

    try:
        # Load vector store and create retriever
        try:
            vector_store = vector_store_manager.load_vector_store()
            retriever = vector_store_manager.as_retriever(vector_store)
        except Exception as e:
            logger.warning("Vector store not available, generating without RAG", error=str(e))
            retriever = None

        # Generate lesson
        generator = LessonGenerator(retriever=retriever)
        lesson = generator.generate_lesson(
            topic=request.topic,
            learner_id=request.learner_id
        )

        # Safety validation
        content_to_validate = f"{lesson.get('content', '')} {lesson.get('scenario', '')}"
        safety_check = safety_validator.validate_content(content_to_validate)

        if not safety_check["passed"]:
            logger.warning("Lesson failed safety check", issues=safety_check["issues"])
            # Sanitize content
            if safety_check.get("pii_detected"):
                lesson["content"] = safety_validator.sanitize_content(lesson["content"])
                lesson["scenario"] = safety_validator.sanitize_content(lesson["scenario"])

        response = LessonResponse(
            lesson=lesson,
            metadata={
                "generated_at": "2025-11-15T00:00:00Z",
                "model": settings.openai_model,
                "rag_enabled": retriever is not None
            },
            safety_check=safety_check
        )

        logger.info("Lesson generated successfully", topic=request.topic)
        return response

    except Exception as e:
        logger.error("Lesson generation failed", error=str(e), topic=request.topic)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest-documents")
async def ingest_documents(
    directory: str,
    background_tasks: BackgroundTasks
):
    """
    Ingest documents into vector store (background task).

    Args:
        directory: Directory containing documents
        background_tasks: FastAPI background tasks

    Returns:
        Task status
    """
    logger.info("Document ingestion requested", directory=directory)

    def ingest():
        from app.ingestion.document_processor import DocumentProcessor

        processor = DocumentProcessor()
        documents = processor.process_directory(directory, file_type="pdf")

        vector_store = vector_store_manager.create_vector_store(documents)
        logger.info("Documents ingested", count=len(documents))

    background_tasks.add_task(ingest)

    return {
        "status": "processing",
        "message": f"Ingesting documents from {directory}"
    }


@router.post("/validate-safety")
async def validate_safety(content: str):
    """
    Validate content for safety.

    Args:
        content: Content to validate

    Returns:
        Safety validation result
    """
    logger.info("Safety validation requested")

    result = safety_validator.validate_content(content)

    return result
