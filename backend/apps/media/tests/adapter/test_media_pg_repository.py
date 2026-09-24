import pytest

from media.adapter.outbound.pg.media_pg_repository import MediaPgRepository
from media.domain.errors import MediaNotFoundError
from media.tests.helpers.builders import ctx, new_photo, new_video

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)


async def test_발급한_미디어는_pending_이고_키가_ID_를_품는다(db_session):
    photo = await MediaPgRepository(db_session).create(A, new_photo())
    video = await MediaPgRepository(db_session).create(A, new_video())
    assert (photo.status, photo.keys.original, photo.keys.display, photo.size_bytes, photo.ready_at) == (
        "pending", f"original/shops/1/{photo.id}.jpg", f"display/shops/1/{photo.id}.jpg", None, None)
    assert (video.keys.original, video.keys.display, video.duration_seconds) == (
        f"original-video/shops/1/{video.id}.mp4", None, 42)


async def test_다른_매장의_미디어는_없는_것이다(db_session):
    photo = await MediaPgRepository(db_session).create(A, new_photo())
    with pytest.raises(MediaNotFoundError):
        await MediaPgRepository(db_session).get(B, photo.id)
    assert await MediaPgRepository(db_session).mark_ready(B, photo.id, 100) is False


async def test_준비는_한_번만_바뀐다(db_session):
    repo = MediaPgRepository(db_session)
    photo = await repo.create(A, new_photo())
    assert await repo.mark_ready(A, photo.id, 1234) is True
    assert await repo.mark_ready(A, photo.id, 9999) is False
    ready = await repo.get(A, photo.id)
    assert (ready.status, ready.size_bytes, ready.ready_at is not None) == ("ready", 1234, True)
