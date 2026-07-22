import logging
from gateway.client import GatewayClient

logger = logging.getLogger("ai_platform.chaos.gateway_failure")

class GatewayFailureSimulator:
    def __init__(self):
        self._original_request = GatewayClient.request

    def inject_timeout_failure(self):
        """Simulate Gateway downstream service HTTP connection timeouts."""
        logger.warning("Injecting Gateway Connection Timeout Chaos...")
        async def mock_timeout(*args, **kwargs):
            raise TimeoutError("Connection to Springfield gateway timed out (Simulated Chaos)")
        
        GatewayClient.request = mock_timeout

    def recover(self):
        """Restore gateway client requests."""
        logger.info("Recovering Gateway Client connections...")
        GatewayClient.request = self._original_request

gateway_failure_simulator = GatewayFailureSimulator()
