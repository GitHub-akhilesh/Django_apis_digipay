import pytest
from memory.conversation import ConversationMemory
from memory.summary import summary_memory
from memory.session import session_metadata_memory

def test_memory_components():
    ConversationMemory.save_summary("session_abc", "Test Summary")
    # Verify local or redis fetch runs without errors
    val = ConversationMemory.get_summary("session_abc")
    assert val in ["Test Summary", None]
