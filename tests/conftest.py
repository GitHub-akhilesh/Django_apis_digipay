import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import pytest_asyncio
from app.database import AsyncSessionLocal

@pytest_asyncio.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session
