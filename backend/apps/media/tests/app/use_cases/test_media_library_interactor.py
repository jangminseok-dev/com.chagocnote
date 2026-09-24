from datetime import datetime, timezone

import pytest

from hub.app.errors import MediaClaimAlreadyAttachedError, MediaClaimNotFoundError, MediaClaimNotReadyError
from media.app.use_cases.media_library_interactor import MediaLibraryInteractor
from media.tests.helpers.builders import ctx
from media.tests.helpers.fakes import NOW, FakeMedia, FakeStorage


def _library():
    media = FakeMedia()
    return MediaLibraryInteractor(media, FakeStorage(), now=lambda: NOW), media


async def test_준비된_미디어를_가져가고_종류를_돌려준다():
    library, media = _library()
    photo, video = media.seed(status="ready"), media.seed(kind="video", status="ready")
    assert await library.claim(ctx(), [photo.id, video.id]) == {photo.id: "photo", video.id: "video"}
    assert media.rows[photo.id].attached_at == media.rows[video.id].attached_at == NOW


@pytest.mark.parametrize("make, error", [
    (lambda m: m.seed(shop_id=2, status="ready"), MediaClaimNotFoundError),
    (lambda m: m.seed(status="pending"), MediaClaimNotReadyError),
    (lambda m: m.seed(status="ready", attached_at=NOW), MediaClaimAlreadyAttachedError),
])
async def test_하나라도_안_되면_아무것도_가져가지_않는다(make, error):
    library, media = _library()
    good = media.seed(status="ready")
    bad = make(media)
    with pytest.raises(error):
        await library.claim(ctx(), [good.id, bad.id])
    assert media.rows[good.id].attached_at is None


async def test_없는_ID_는_NOT_FOUND_다():
    library, media = _library()
    good = media.seed(status="ready")
    with pytest.raises(MediaClaimNotFoundError):
        await library.claim(ctx(), [good.id, 999])


async def test_놓으면_다시_가져갈_수_있다():
    library, media = _library()
    photo = media.seed(status="ready")
    await library.claim(ctx(), [photo.id])
    await library.release(ctx(), [photo.id])
    assert await library.claim(ctx(), [photo.id]) == {photo.id: "photo"}


async def test_빈_목록은_저장소를_부르지_않는다():
    library, media = _library()
    assert (await library.claim(ctx(), []), await library.read_urls(ctx(), [])) == ({}, {})
    await library.release(ctx(), [])
    assert media.journal == []


async def test_읽기_URL_은_준비된_것만_매장_시간대의_하루_창으로_서명한다():
    library, media = _library()
    photo, video, pending = media.seed(status="ready"), media.seed(kind="video", status="ready"), media.seed()
    urls = await library.read_urls(ctx(), [photo.id, video.id, pending.id])
    assert set(urls) == {photo.id, video.id}
    # NOW 는 서울 12:00 → 창은 그날 04:00(UTC 전날 19:00).
    assert urls[photo.id].thumb_url == f"get://thumb/shops/1/{photo.id}.jpg?signed=20260923T1900"
    assert urls[photo.id].display_url == f"get://display/shops/1/{photo.id}.jpg?signed=20260923T1900"
    assert (urls[video.id].kind, urls[video.id].display_url, urls[video.id].duration_seconds) == ("video", None, 30)
    assert urls[video.id].original_url == f"get://original-video/shops/1/{video.id}.mp4?signed=20260923T1900"


async def test_다른_매장의_미디어는_URL_이_없다():
    library, media = _library()
    photo = media.seed(shop_id=2, status="ready")
    assert await library.read_urls(ctx(), [photo.id]) == {}
