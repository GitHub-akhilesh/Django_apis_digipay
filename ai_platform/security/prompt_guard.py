import logging
from core.exceptions import AuthenticationException

logger = logging.getLogger("ai_platform.security.prompt_guard")

INJECTION_PATTERNS = [
    "ignore previous instructions",
    "reveal system prompt",
    "reveal your system prompt",
    "show hidden tools",
    "print api key",
    "bypass authentication",
    "execute tool directly"
]

class PromptGuard:
    @staticmethod
    def validate_prompt(prompt: str):
        """Scans user inputs for prompt injection attack patterns."""
        if not prompt:
            return

        normalized = prompt.lower()
        for pattern in INJECTION_PATTERNS:
            if pattern in normalized:
                logger.warning(f"Adversarial prompt injection pattern detected: '{pattern}'")
                raise AuthenticationException(
                    f"Security Exception: Adversarial query pattern '{pattern}' rejected by AI PromptGuard."
                )

prompt_guard = PromptGuard()
