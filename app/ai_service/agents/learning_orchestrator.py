from langchain_anthropic import ChatAnthropic
from langchain.agents import create_agent
from app.config.settings import settings
from agents.tools import AGENT_TOOLS
from agents.memory_manager import LearningMemoryManager
import structlog
from typing import Dict, Any

logger = structlog.get_logger()

class LearningOrchestrator:
    """Agent that orchestrates personalized learning paths."""

    def __init__(self):
        """Initialize the orchestrator with LLM and tools."""
        self.llm = ChatAnthropic(
            model=settings.anthropic_model,
            temperature=settings.agent_temperature,
            anthropic_api_key=settings.anthropic_api_key
        )
        self.tools = AGENT_TOOLS
        self.memory_manager = LearningMemoryManager()
        
        # Create the agent graph
        self.agent_graph = self._create_agent_graph()

    def _create_agent_graph(self):
        """Create the agent graph with tool calling."""
        
        system_prompt = """You are an expert Adaptive Learning Assistant for the BMO Learning Platform.
        Your goal is to guide learners through financial topics, specifically business credit cards.
        
        Process:
        1. Assess the learner's current knowledge if not known.
        2. Identify knowledge gaps.
        3. Generate personalized lessons using the 'generate_adaptive_lesson' tool.
        4. Create practice scenarios using 'create_practice_scenario'.
        5. Evaluate understanding with quizzes using 'evaluate_quiz_response'.
        6. Adjust the learning path based on performance using 'get_learning_path'.
        
        Principles:
        - Start easy for beginners, increase difficulty gradually.
        - Reinforce weak areas identified in assessments.
        - Keep lessons concise (under 3 minutes reading time).
        - Use real-world BMO scenarios.
        - Be encouraging and professional.
        
        Always check the learner's context before generating content.
        """
        
        return create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=system_prompt
        )

    async def orchestrate_learning_session(self, learner_id: str, request: str) -> Dict[str, Any]:
        """
        Handle a complete learning interaction.
        
        Args:
            learner_id: Unique learner identifier
            request: User's input or request
            
        Returns:
            Structured response from the agent
        """
        logger.info("Orchestrating session", learner_id=learner_id)
        
        # Get learner context
        context = await self.memory_manager.get_learner_context(learner_id)
        
        try:
            # Prepare messages with context
            messages = [
                {"role": "user", "content": request}
            ]
            
            # Execute agent
            result_messages = []
            async for chunk in self.agent_graph.astream(
                {"messages": messages},
                stream_mode="values"
            ):
                if "messages" in chunk:
                    result_messages = chunk["messages"]
            
            # Get the last message as output
            if result_messages:
                output = result_messages[-1].content if hasattr(result_messages[-1], 'content') else str(result_messages[-1])
            else:
                output = "I apologize, but I couldn't process your request."
            
            # Update learner progress
            await self.memory_manager.update_learner_progress(
                learner_id, 
                {"type": "chat", "topic": "general", "interaction": request}
            )
            
            return {
                "response": output,
                "learner_id": learner_id,
                "status": "success"
            }
            
        except Exception as e:
            logger.error("Agent execution failed", error=str(e))
            return {
                "response": "I apologize, but I encountered an error processing your request. Please try again.",
                "error": str(e),
                "status": "error"
            }

    async def adaptive_lesson_flow(self, learner_id: str, topic: str) -> Dict[str, Any]:
        """
        Execute a specific adaptive learning flow for a topic.
        
        Args:
            learner_id: Unique learner identifier
            topic: Topic to learn
            
        Returns:
            Complete learning package
        """
        logger.info("Starting adaptive lesson flow", learner_id=learner_id, topic=topic)
        
        request = f"I want to learn about {topic}. Please assess my knowledge and generate a lesson for me."
        return await self.orchestrate_learning_session(learner_id, request)
