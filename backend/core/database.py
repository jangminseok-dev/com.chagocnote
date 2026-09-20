from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from core.config import DATABASE_URL


class Base(DeclarativeBase):
    pass


engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine() -> None:
    global engine, _session_factory
    if engine is not None:
        return
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
    _session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def dispose_engine() -> None:
    global engine, _session_factory
    if engine is not None:
        await engine.dispose()
    engine = None
    _session_factory = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """요청 하나에 세션 하나. 성공하면 커밋하고 예외가 나면 롤백한다."""
    if _session_factory is None:
        init_engine()
    assert _session_factory is not None
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# 요청 함수가 끝나는 즉시(응답을 보내기 전에) 커밋되도록 function 스코프로 정리한다.
# 기본 스코프는 응답 본문을 보낸 뒤에 정리되어, 클라이언트가 커밋 전 데이터를 보지 못한 채 200을 받는다.
DbSession = Annotated[AsyncSession, Depends(get_db, scope="function")]
