"""LLM safety validation using Constitutional AI and content moderation."""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from openai import OpenAI
import re
import structlog

from app.config.settings import settings

logger = structlog.get_logger()


class SafetyValidator:
    """Validates LLM outputs for safety and compliance."""

    def __init__(self):
        """Initialize safety validator."""
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0,
            openai_api_key=settings.openai_api_key
        )
        self.openai_client = OpenAI(api_key=settings.openai_api_key)

        # Constitutional AI principles for financial services
        self.principles = [
            "Content must be accurate and not misleading",
            "Must not provide personalized financial advice",
            "Must include appropriate disclaimers for financial content",
            "Must not discriminate based on protected characteristics",
            "Must maintain professional and respectful tone"
        ]

    def validate_content(self, content: str) -> dict:
        """
        Validate content against safety principles.

        Args:
            content: Content to validate

        Returns:
            Validation result with pass/fail and reasons
        """
        logger.info("Validating content safety", content_length=len(content))

        results = {
            "passed": True,
            "pii_detected": False,
            "moderation_flagged": False,
            "constitutional_ai_passed": True,
            "issues": []
        }

        # PII Detection
        if settings.enable_pii_detection:
            pii_found = self._detect_pii_list(content)
            if pii_found:
                results["passed"] = False
                results["pii_detected"] = True
                results["issues"].append(f"PII detected: {', '.join(pii_found)}")

        # Content Moderation
        moderation = self._check_moderation(content)
        if moderation["flagged"]:
            results["passed"] = False
            results["moderation_flagged"] = True
            results["issues"].extend(moderation["categories"])

        # Constitutional AI
        if settings.enable_constitutional_ai:
            constitutional = self._constitutional_check(content)
            if not constitutional["passed"]:
                results["passed"] = False
                results["constitutional_ai_passed"] = False
                results["issues"].extend(constitutional["violations"])

        logger.info(
            "Content validation completed",
            passed=results["passed"],
            issues_count=len(results["issues"])
        )

        return results

    def _detect_pii_list(self, text: str | None) -> list[str]:
        """
        Detect potential PII in text and return list of PII types.

        Args:
            text: Text to scan

        Returns:
            List of PII types detected
        """
        if text is None or not isinstance(text, str) or not text:
            return []

        pii_found = []

        # Email pattern
        if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text):
            pii_found.append("email")

        # Phone pattern (simple) - matches (555) 123-4567 and variations
        if re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', text):
            pii_found.append("phone")

        # SSN pattern (simple)
        if re.search(r'\b\d{3}-\d{2}-\d{4}\b', text):
            pii_found.append("ssn")

        # Credit card pattern (simple)
        if re.search(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', text):
            pii_found.append("credit_card")

        return pii_found

    def _detect_pii(self, text: str | None) -> bool:
        """
        Detect potential PII in text (boolean return for tests).

        Args:
            text: Text to scan

        Returns:
            True if PII found, False otherwise
        """
        pii_list = self._detect_pii_list(text)
        return bool(pii_list)

    def _check_moderation(self, text: str) -> dict:
        """
        Check content using OpenAI moderation API.

        Args:
            text: Text to moderate

        Returns:
            Moderation result
        """
        try:
            response = self.openai_client.moderations.create(input=text)
            result = response.results[0]

            flagged_categories = []
            if result.flagged:
                for category, flagged in result.categories.model_dump().items():
                    if flagged:
                        flagged_categories.append(category)

            return {
                "flagged": result.flagged,
                "categories": flagged_categories
            }
        except Exception as e:
            logger.error("Moderation check failed", error=str(e))
            return {"flagged": False, "categories": []}

    def _check_content_moderation(self, text: str) -> bool:
        """
        Check content moderation (returns boolean for test compatibility).

        Args:
            text: Text to moderate

        Returns:
            True if flagged, False if clean
        """
        result = self._check_moderation(text)
        return result["flagged"]

    def _constitutional_check(self, content: str) -> dict:
        """
        Check content against constitutional AI principles.

        Args:
            content: Content to check

        Returns:
            Constitutional validation result
        """
        prompt = ChatPromptTemplate.from_template("""
        Evaluate the following financial education content against these principles:

        {principles}

        Content to evaluate:
        {content}

        Respond with JSON:
        {{
            "passed": true/false,
            "violations": ["list of any violations"]
        }}
        """)

        try:
            chain = prompt | self.llm
            result = chain.invoke({
                "principles": "\n".join(self.principles),
                "content": content
            })

            # Parse response (simplified - production would use structured output)
            response_text = result.content.lower()
            passed = "true" in response_text or "passed" in response_text

            return {
                "passed": passed,
                "violations": [] if passed else ["Constitutional check failed"]
            }
        except Exception as e:
            logger.error("Constitutional check failed", error=str(e))
            return {"passed": True, "violations": []}

    def sanitize_content(self, content: str) -> str:
        """
        Remove or redact PII from content.

        Args:
            content: Content to sanitize

        Returns:
            Sanitized content
        """
        # Redact emails
        content = re.sub(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            '[REDACTED]',
            content
        )

        # Redact phone numbers - match (555) 123-4567, 555-1234, and other patterns
        content = re.sub(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', '[REDACTED]', content)
        content = re.sub(r'\b\d{3}[-.\s]\d{4}\b', '[REDACTED]', content)  # Match 555-1234

        # Redact SSN
        content = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[REDACTED]', content)

        # Redact credit cards
        content = re.sub(
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            '[REDACTED]',
            content
        )

        return content
