import pytest

from media.app.dtos.confirm_upload_dto import ConfirmUploadCommand
from media.app.use_cases.confirm_upload_interactor import ConfirmUploadInteractor
from media.domain.errors import (
    MediaNotFoundError,
    MediaNotUploadedError,
    MediaTooLargeError,
    MediaTypeUnsupportedError,
)
from media.tests.helpers.builders import ctx
from media.tests.helpers.fakes import FakeMedia, FakeStorage, Journal

MB = 1024 * 1024


def _setup(kind="photo"):
    journal = Journal()
    media, storage = FakeMedia(journal), FakeStorage(journal)
    row = media.seed(kind=kind)
    return ConfirmUploadInteractor(media, storage), media, storage, row, journal


def _upload_all(storage, row, original_size=3 * MB, original_type=None):
    storage.put(row.keys.original, original_size, original_type or row.content_type)
    for key in row.keys.all()[1:]:
        storage.put(key, 200_000)


async def test_객체가_다_있으면_원본_크기로_ready_가_된다():
    interactor, media, storage, row, journal = _setup()
    _upload_all(storage, row)
    view = await interactor.confirm_upload(ConfirmUploadCommand(ctx=ctx(member_id=99), media_id=row.id))
    assert (view.status, view.size_bytes) == ("ready", 3 * MB)
    assert [e[0] for e in journal] == ["head", "head", "head", "mark_ready"]


async def test_하나라도_없으면_409_MEDIA_NOT_UPLOADED_이고_아무것도_바꾸지_않는다():
    interactor, media, storage, row, journal = _setup()
    storage.put(row.keys.original, MB)
    with pytest.raises(MediaNotUploadedError):
        await interactor.confirm_upload(ConfirmUploadCommand(ctx=ctx(), media_id=row.id))
    assert media.rows[row.id].status == "pending"
    assert not [e for e in journal if e[0] in ("mark_ready", "delete")]


@pytest.mark.parametrize("kind, size, content_type, error", [
    ("photo", 20 * MB + 1, None, MediaTooLargeError),
    ("video", 200 * MB + 1, None, MediaTooLargeError),
    ("photo", MB, "image/png", MediaTypeUnsupportedError),
])
async def test_한도를_넘거나_형식이_다르면_객체를_지우고_거절한다(kind, size, content_type, error):
    interactor, media, storage, row, journal = _setup(kind)
    _upload_all(storage, row, size, content_type)
    with pytest.raises(error):
        await interactor.confirm_upload(ConfirmUploadCommand(ctx=ctx(), media_id=row.id))
    assert storage.objects == {}
    assert ("delete", row.keys.all()) in journal
    assert media.rows[row.id].status == "pending"


async def test_썸네일도_JPEG_이고_사진_한도_안이어야_한다():
    interactor, media, storage, row, _ = _setup("video")
    _upload_all(storage, row)
    storage.put(row.keys.thumb, 21 * MB)
    with pytest.raises(MediaTooLargeError):
        await interactor.confirm_upload(ConfirmUploadCommand(ctx=ctx(), media_id=row.id))


async def test_이미_ready_면_저장소를_보지_않고_그대로_준다():
    interactor, media, storage, _, journal = _setup()
    ready = media.seed(status="ready")
    view = await interactor.confirm_upload(ConfirmUploadCommand(ctx=ctx(), media_id=ready.id))
    assert (view.status, journal) == ("ready", [])


async def test_다른_매장의_미디어는_404_다():
    interactor, _, _, row, _ = _setup()
    with pytest.raises(MediaNotFoundError):
        await interactor.confirm_upload(ConfirmUploadCommand(ctx=ctx(shop_id=2), media_id=row.id))
