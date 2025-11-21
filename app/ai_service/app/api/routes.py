"""API routes for AI service."""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional
import structlog

from app.generators.lesson_generator import LessonGenerator, LessonContent
from app.safety.safety_validator import SafetyValidator
from app.ingestion.vector_store import VectorStoreManager
from app.ingestion.document_processor import DocumentProcessor
from app.storage.s3_client import S3Client
from app.config.settings import settings
import time

router = APIRouter()
logger = structlog.get_logger()

# Initialize components
vector_store_manager = VectorStoreManager()
safety_validator = SafetyValidator()
s3_client = S3Client()


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


class DocumentProcessingRequest(BaseModel):
    """Document processing request from Rails API."""
    document_id: int = Field(..., description="Document ID from Rails database")
    s3_bucket: str = Field(..., description="S3 bucket name")
    s3_key: str = Field(..., description="S3 object key")
    content_type: str = Field(..., description="MIME type of the document")
    filename: str = Field(..., description="Original filename")
    category: Optional[str] = Field(None, description="Document category")
    metadata: Optional[dict] = Field(None, description="Additional metadata")


class DocumentProcessingResponse(BaseModel):
    """Document processing response."""
    success: bool = Field(..., description="Whether processing succeeded")
    chunks_created: int = Field(0, description="Number of text chunks created")
    embeddings_created: int = Field(0, description="Number of embeddings created")
    processing_time_seconds: float = Field(..., description="Processing time in seconds")
    error: Optional[str] = Field(None, description="Error message if failed")


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
                "model": settings.anthropic_model,
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


@router.post("/process-document", response_model=DocumentProcessingResponse)
async def process_document(request: DocumentProcessingRequest):
    """
    Process a document from S3 for RAG ingestion.

    This endpoint is called by the Rails API DocumentProcessingJob to:
    1. Download the document from S3
    2. Extract text and chunk it for RAG
    3. Generate embeddings
    4. Store in the vector database (Chroma)

    Args:
        request: Document processing request with S3 location and metadata

    Returns:
        Processing statistics (chunks, embeddings, processing time)

    Raises:
        HTTPException: If processing fails
    """
    start_time = time.time()

    logger.info(
        "Document processing requested",
        document_id=request.document_id,
        s3_bucket=request.s3_bucket,
        s3_key=request.s3_key,
        filename=request.filename
    )

    try:
        # Build S3 URI
        s3_uri = f"s3://{request.s3_bucket}/{request.s3_key}"

        # Determine file type from content_type or filename
        file_type = "pdf"
        if request.content_type:
            if "pdf" in request.content_type.lower():
                file_type = "pdf"
            elif "text" in request.content_type.lower():
                file_type = "txt"
        elif request.filename:
            if request.filename.lower().endswith(".pdf"):
                file_type = "pdf"
            elif request.filename.lower().endswith(".txt"):
                file_type = "txt"

        logger.debug(
            "Processing document from S3",
            s3_uri=s3_uri,
            file_type=file_type
        )

        # Process document from S3
        processor = DocumentProcessor()
        documents = processor.process_s3_file(
            s3_uri=s3_uri,
            file_type=file_type,
            s3_client=s3_client
        )

        # Chunk documents
        chunks = processor.chunk_documents(documents)

        # Add metadata if provided
        if request.metadata:
            chunks = processor.add_metadata(chunks, request.metadata)

        # Add standard metadata
        standard_metadata = {
            "document_id": request.document_id,
            "filename": request.filename,
            "category": request.category,
            "s3_uri": s3_uri
        }
        chunks = processor.add_metadata(chunks, standard_metadata)

        logger.debug(
            "Document chunked",
            document_count=len(documents),
            chunk_count=len(chunks)
        )

        # Store in vector database
        try:
            vector_store = vector_store_manager.load_vector_store()
            logger.debug("Loaded existing vector store")
        except Exception as e:
            logger.info("Creating new vector store", error=str(e))
            vector_store = None

        if vector_store is None:
            # Create new vector store with chunks
            vector_store = vector_store_manager.create_vector_store(chunks)
            embeddings_created = len(chunks)
        else:
            # Add chunks to existing vector store
            vector_store_manager.add_documents(vector_store, chunks)
            embeddings_created = len(chunks)

        processing_time = time.time() - start_time

        logger.info(
            "Document processing completed",
            document_id=request.document_id,
            chunks_created=len(chunks),
            embeddings_created=embeddings_created,
            processing_time=processing_time
        )

        return DocumentProcessingResponse(
            success=True,
            chunks_created=len(chunks),
            embeddings_created=embeddings_created,
            processing_time_seconds=round(processing_time, 2)
        )

    except FileNotFoundError as e:
        processing_time = time.time() - start_time
        error_msg = f"Document not found in S3: {str(e)}"

        logger.error(
            "Document not found",
            document_id=request.document_id,
            s3_uri=s3_uri,
            error=error_msg
        )

        return DocumentProcessingResponse(
            success=False,
            chunks_created=0,
            embeddings_created=0,
            processing_time_seconds=round(processing_time, 2),
            error=error_msg
        )

    except ValueError as e:
        processing_time = time.time() - start_time
        error_msg = f"Invalid document or configuration: {str(e)}"

        logger.error(
            "Document processing validation error",
            document_id=request.document_id,
            error=error_msg
        )

        return DocumentProcessingResponse(
            success=False,
            chunks_created=0,
            embeddings_created=0,
            processing_time_seconds=round(processing_time, 2),
            error=error_msg
        )

    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = f"Document processing failed: {str(e)}"

        logger.error(
            "Document processing failed",
            document_id=request.document_id,
            error=str(e),
            error_type=type(e).__name__
        )

        raise HTTPException(
            status_code=500,
            detail=error_msg
        )
