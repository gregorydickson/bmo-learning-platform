"""Lesson content generation using LangChain LCEL."""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough
from pydantic import BaseModel, Field
from typing import List
import structlog

from app.config.settings import settings

logger = structlog.get_logger()


class LessonContent(BaseModel):
    """Structured lesson output."""
    topic: str = Field(description="The topic of the lesson")
    content: str = Field(description="Main lesson content")
    key_points: List[str] = Field(description="3-5 key takeaways")
    scenario: str = Field(description="Real-world scenario example")
    quiz_question: str = Field(description="Multiple choice question")
    quiz_options: List[str] = Field(description="4 answer options")
    correct_answer: int = Field(description="Index of correct answer (0-3)")


class LessonGenerator:
    """Generates microlearning lessons using RAG and LLM."""

    def __init__(self, retriever=None):
        """
        Initialize lesson generator.

        Args:
            retriever: Document retriever for RAG
        """
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.7,
            openai_api_key=settings.openai_api_key
        )
        self.retriever = retriever
        self.parser = JsonOutputParser(pydantic_object=LessonContent)

    def create_lesson_chain(self):
        """
        Create LCEL chain for lesson generation.

        Returns:
            Runnable chain
        """
        # Prompt template
        template = """You are an expert financial educator creating microlearning content about business credit cards.

        Context from knowledge base:
        {context}

        Create an engaging, concise lesson about: {topic}

        The lesson should:
        - Be 2-3 paragraphs (max 200 words)
        - Use simple language suitable for business professionals
        - Include a relatable real-world scenario
        - End with a multiple-choice quiz question

        {format_instructions}
        """

        prompt = ChatPromptTemplate.from_template(template)

        # Build chain using LCEL
        if self.retriever:
            chain = (
                {
                    "context": lambda x: self._format_docs(
                        self.retriever.get_relevant_documents(x["topic"])
                    ),
                    "topic": lambda x: x["topic"],
                    "format_instructions": lambda x: self.parser.get_format_instructions()
                }
                | prompt
                | self.llm
                | self.parser
            )
        else:
            chain = (
                {
                    "context": lambda x: "No context available",
                    "topic": lambda x: x["topic"],
                    "format_instructions": lambda x: self.parser.get_format_instructions()
                }
                | prompt
                | self.llm
                | self.parser
            )

        return chain

    def _format_docs(self, docs) -> str:
        """Format documents for context."""
        return "\n\n".join([doc.page_content for doc in docs])

    def generate_lesson(self, topic: str, learner_id: str | None = None) -> dict:
        """
        Generate a complete lesson.

        Args:
            topic: Lesson topic
            learner_id: Optional learner ID for personalization

        Returns:
            Lesson content dictionary
        """
        logger.info("Generating lesson", topic=topic, learner_id=learner_id)

        chain = self.create_lesson_chain()

        try:
            result = chain.invoke({"topic": topic})
            logger.info("Lesson generated successfully", topic=topic)
            return result
        except Exception as e:
            logger.error("Lesson generation failed", topic=topic, error=str(e))
            raise


class QuizGenerator:
    """Generates quiz questions for lessons."""

    def __init__(self):
        """Initialize quiz generator."""
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.8,
            openai_api_key=settings.openai_api_key
        )

    def generate_quiz(
        self,
        lesson_content: str,
        difficulty: str = "medium"
    ) -> dict:
        """
        Generate quiz question from lesson content.

        Args:
            lesson_content: Lesson text
            difficulty: Question difficulty (easy/medium/hard)

        Returns:
            Quiz question dictionary
        """
        logger.info("Generating quiz", difficulty=difficulty)

        prompt = f"""Based on this lesson content:

        {lesson_content}

        Create a {difficulty} difficulty multiple-choice question with 4 options.
        Return as JSON with keys: question, options (array), correct_answer (index 0-3).
        """

        response = self.llm.invoke(prompt)

        logger.info("Quiz generated")
        return {"quiz": response.content}
