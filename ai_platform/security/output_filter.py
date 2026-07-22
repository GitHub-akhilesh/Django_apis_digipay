import logging

logger = logging.getLogger("ai_platform.security.output_filter")

STACKTRACE_PATTERNS = [
    "traceback (most recent call last)",
    "file \"",
    "line ",
    "exception in thread",
    "at org.springframework"
]

class OutputValidationGuard:
    @staticmethod
    def sanitize_output(output_text: str) -> str:
        """Sanitizes output by checking for stack trace leaks and developer secrets."""
        if not output_text:
            return output_text

        normalized = output_text.lower()
        
        # 1. Stacktrace checks
        for pattern in STACKTRACE_PATTERNS:
            if pattern in normalized:
                logger.warning("Stack trace leak detected in LLM response! Redacting.")
                return "The system encountered an error. Support ticket has been auto-logged. Please retry."

        # 2. Prevent system instructions leakage
        if "you are a support agent" in normalized or "Knowledge Base Document:" in output_text:
            logger.warning("System prompt instruction leakage detected! Redacting.")
            return "Answer is redacted due to internal system security policies."

        return output_text

output_validation_guard = OutputValidationGuard()
