import time
import asyncio
import logging
from gateway.client import GatewayClient

logger = logging.getLogger("ai_platform.chaos.network_failure")

class NetworkLatencySimulator:
    def __init__(self):
        self._original_request = GatewayClient.request

    def inject_latency(self, delay_sec: float):
        """Simulate Network packet latency by delaying all client Gateway requests."""
        logger.warning(f"Injecting Network Latency Chaos: delay={delay_sec}s...")
        
        async def delayed_request(*args, **kwargs):
            await asyncio.sleep(delay_sec)
            return await self._original_request(*args, **kwargs)
            
        GatewayClient.request = delayed_request

    def recover(self):
        """Restore request timing."""
        logger.info("Recovering Network Latency...")
        GatewayClient.request = self._original_request

network_latency_simulator = NetworkLatencySimulator()
