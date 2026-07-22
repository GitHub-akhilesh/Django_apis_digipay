import asyncio
import logging
from typing import AsyncGenerator
from streaming.events import StreamEvent, EventType

logger = logging.getLogger("ai_platform.streaming.token_stream")

class TokenStreamer:
    @staticmethod
    async def stream_tokens(full_text: str, delay_ms: float = 20) -> AsyncGenerator[str, None]:
        """Yield text token by token for real-time frontend rendering."""
        words = full_text.split()
        for idx, word in enumerate(words):
            token_text = word + (" " if idx < len(words) - 1 else "")
            event = StreamEvent(
                event_type=EventType.TOKEN_GENERATED,
                data={"token": token_text, "index": idx}
            )
            yield event.to_sse()
            await asyncio.sleep(delay_ms / 1000.0)

token_streamer = TokenStreamer()
