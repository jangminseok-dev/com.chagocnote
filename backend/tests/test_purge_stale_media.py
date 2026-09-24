"""미디어 정리 스크립트 — 하루 넘게 어느 기록도 가져가지 않은 것만 지운다."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update

import scripts.purge_stale_media as purge_stale_media
from media.adapter.outbound.orm.media_orm import MediaObjectOrm
from media.adapter.outbound.pg.media_pg_repository import MediaPgRepository
from media.tests.helpers.builders import ctx, new_photo, new_video
from media.tests.helpers.fakes import FakeStorage
from scripts.purge_stale_media import purge

pytestmark = pytest.mark.integration

NOW = datetime(2026, 9, 24, 3, 0, tzinfo=timezone.utc)
OLD, FRESH = NOW - timedelta(hours=25), NOW - timedelta(hours=23)


async def _media(session, kind="photo", status="pending", at=OLD, attached=False):
    repo = MediaPgRepository(session)
    media = await repo.create(ctx(), new_photo() if kind == "photo" else new_video())
    if status == "ready":
        await repo.mark_ready(ctx(), media.id, 100)
    await session.execute(
        update(MediaObjectOrm).where(MediaObjectOrm.id == media.id)
        .values(created_at=at, ready_at=at if status == "ready" else None, attached_at=at if attached else None)
    )
    await session.commit()
    return media


async def test_하루_넘은_pending_과_놓인_ready_만_저장소와_표에서_지운다(db_session):
    old_pending = await _media(db_session)
    old_loose = await _media(db_session, kind="video", status="ready")
    kept = [await _media(db_session, at=FRESH), await _media(db_session, status="ready", at=FRESH),
            await _media(db_session, status="ready", attached=True)]
    storage = FakeStorage()
    assert await purge(db_session, storage, NOW) == 2
    remaining = set((await db_session.execute(select(MediaObjectOrm.id))).scalars())
    assert remaining == {m.id for m in kept}
    assert [e for e in storage.journal if e[0] == "delete"] == [
        ("delete", old_pending.keys.all()), ("delete", old_loose.keys.all())]


async def test_저장소_삭제_중에_멈춰도_다시_돌리면_지운다(db_session):
    media = await _media(db_session, status="ready")

    class _Broken(FakeStorage):
        async def delete(self, keys):
            raise ConnectionError("저장소가 응답하지 않는다")

    with pytest.raises(ConnectionError):
        await purge(db_session, _Broken(), NOW)
    await db_session.rollback()
    row = (await db_session.execute(select(MediaObjectOrm).where(MediaObjectOrm.id == media.id))).scalar_one()
    assert (row.status, row.ready_at) == ("pending", None)   # 가져갈 수 없게 표시된 채 남았다
    assert await purge(db_session, FakeStorage(), NOW) == 1


async def test_고른_뒤_기록이_가져간_미디어는_건너뛴다(db_session):
    first = await _media(db_session, status="ready")
    second = await _media(db_session, status="ready")

    class _Racing(FakeStorage):
        """첫 객체를 지우는 사이 다른 요청이 둘째를 기록에 붙인다."""

        async def delete(self, keys):
            await super().delete(keys)
            if keys == list(first.keys.all()):
                await db_session.execute(update(MediaObjectOrm).where(MediaObjectOrm.id == second.id)
                                         .values(attached_at=NOW))
                await db_session.commit()

    assert await purge(db_session, _Racing(), NOW) == 1
    assert set((await db_session.execute(select(MediaObjectOrm.id))).scalars()) == {second.id}


async def test_정리_스크립트의_엔진도_hide_parameters를_켠다(migrated_test_db, monkeypatch):
    captured = {}
    original = purge_stale_media.create_async_engine

    def _spy(url, **kwargs):
        captured.update(kwargs)
        return original(url, **kwargs)

    monkeypatch.setattr(purge_stale_media, "create_async_engine", _spy)
    monkeypatch.setattr(purge_stale_media, "DATABASE_URL", migrated_test_db)
    monkeypatch.setattr(purge_stale_media, "get_object_storage", FakeStorage)
    await purge_stale_media._run()
    assert captured.get("hide_parameters") is True
