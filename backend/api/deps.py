from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import SessionLocal


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


# v1: single-user mode, always user_id=1
async def current_user_id() -> int:
    return 1


SessionDep = Depends(get_session)
UserDep = Depends(current_user_id)
