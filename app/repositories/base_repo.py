import logging
from typing import Generic, TypeVar, Type, Optional, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger("digipay")
T = TypeVar("T")

class BaseRepository(Generic[T]):
    """Base Async SQLAlchemy Repository providing standard CRUD patterns."""
    
    def __init__(self, model: Type[T]):
        self.model = model

    async def get_by_id(self, db: AsyncSession, id_val: Any) -> Optional[T]:
        stmt = select(self.model).where(self.model.id == id_val)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_all(self, db: AsyncSession, limit: int = 100) -> List[T]:
        stmt = select(self.model).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all())
