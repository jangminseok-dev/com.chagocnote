"""하루 넘게 어느 기록도 가져가지 않은 미디어를 저장소와 표에서 지운다(설계 7.5). 여러 번 돌려도 결과가 같다.

지우는 것: ① 발급만 하고 하루 넘게 확인하지 않은 것(pending) ② 확인했거나 놓인 뒤 하루 넘게 어느 기록도 가져가지 않은 것 —
기록에서 뺐거나 기록을 지워 놓인 사진도 여기로 온다. 놓기(`detach`)가 `ready_at`을 다시 찍으므로 하루는 놓인 시각부터 센다
(놓인 뒤 바로 지우지 않는다 — 되돌리기·대기열 재시도의 여유).
한 객체씩 ① 행을 pending 으로 되돌려 커밋하고(그사이 기록이 가져가지 못한다) ② 저장소에서 지우고 ③ 행을 지워 커밋한다.
②에서 멈추면 행이 오래된 pending 으로 남아 다음 실행이 ①로 다시 잡는다. 잠금을 쥔 채 저장소를 부르지 않는다.
사용: cd infra && docker compose run --rm backend python scripts/purge_stale_media.py
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import DATABASE_URL
from media.adapter.outbound.orm.media_orm import MediaObjectOrm as Media
from media.app.ports.output.object_storage_port import ObjectStoragePort
from media.dependencies.media_wiring import get_object_storage

KEEP_FOR = timedelta(hours=24)


def _stale(cutoff: datetime):
    return or_(
        and_(Media.status == "pending", Media.created_at < cutoff),
        and_(Media.status == "ready", Media.attached_at.is_(None), Media.ready_at < cutoff),
    )


async def purge(session: AsyncSession, storage: ObjectStoragePort, now: datetime) -> int:
    """지운 미디어 수를 돌려준다. 객체마다 짧게 커밋한다."""
    cutoff = now - KEEP_FOR
    found = (
        await session.execute(
            select(Media.id, Media.object_key, Media.display_key, Media.thumb_key).where(_stale(cutoff)).order_by(Media.id)
        )
    ).all()
    purged = 0
    for media_id, *keys in found:
        # 조건을 다시 본다 — 고른 뒤 기록이 가져갔으면 건너뛴다. pending 으로 되돌리면 이제 가져갈 수 없다.
        marked = await session.execute(
            update(Media).where(Media.id == media_id, _stale(cutoff))
            .values(status="pending", ready_at=None, size_bytes=None)
        )
        await session.commit()
        if marked.rowcount != 1:
            continue
        await storage.delete([key for key in keys if key is not None])
        await session.execute(delete(Media).where(Media.id == media_id, Media.status == "pending"))
        await session.commit()
        purged += 1
    return purged


async def _run() -> int:
    engine = create_async_engine(DATABASE_URL, hide_parameters=True)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            return await purge(session, get_object_storage(), datetime.now(timezone.utc))
    finally:
        await engine.dispose()


def main() -> None:
    print(f"미디어 {asyncio.run(_run())}개를 지웠습니다.")


if __name__ == "__main__":
    main()
