from datetime import timedelta

import pytest

from media.app.dtos.issue_upload_dto import IssueUploadCommand
from media.app.use_cases.issue_upload_interactor import IssueUploadInteractor
from media.domain.errors import MediaTooLargeError, MediaTypeUnsupportedError
from media.tests.helpers.builders import ctx
from media.tests.helpers.fakes import NOW, FakeMedia, FakeStorage, Journal


def _command(kind="photo", content_type="image/jpeg", byte_size=4_000_000, duration=None):
    return IssueUploadCommand(ctx=ctx(member_id=12), kind=kind, content_type=content_type, byte_size=byte_size,
                              width=3000, height=2000, duration_seconds=duration)


def _interactor(journal=None):
    media = FakeMedia(journal)
    return IssueUploadInteractor(media, FakeStorage(journal), now=lambda: NOW), media


async def test_사진은_렌디션_셋의_PUT_URL_을_15분_동안_준다():
    interactor, media = _interactor()
    view = await interactor.issue_upload(_command())
    row = media.rows[view.media_id]
    assert (row.status, row.uploaded_by_member_id, row.shop_id) == ("pending", 12, 1)
    assert view.puts.original == f"put://original/shops/1/{view.media_id}.jpg?type=image/jpeg&expires=900"
    assert view.puts.display == f"put://display/shops/1/{view.media_id}.jpg?type=image/jpeg&expires=900"
    assert view.puts.thumb == f"put://thumb/shops/1/{view.media_id}.jpg?type=image/jpeg&expires=900"
    assert view.expires_at == NOW + timedelta(minutes=15)


async def test_영상은_원본과_JPEG_포스터_둘이다():
    interactor, _ = _interactor()
    view = await interactor.issue_upload(_command("video", "video/mp4", 150_000_000, duration=42))
    assert view.puts.original.endswith(".mp4?type=video/mp4&expires=900")
    assert (view.puts.display, view.puts.thumb.endswith(".jpg?type=image/jpeg&expires=900")) == (None, True)


@pytest.mark.parametrize("command, error", [
    (_command(content_type="image/heic"), MediaTypeUnsupportedError),
    (_command(byte_size=20 * 1024 * 1024 + 1), MediaTooLargeError),
])
async def test_규칙에_어긋나면_행을_만들지_않는다(command, error):
    journal = Journal()
    interactor, _ = _interactor(journal)
    with pytest.raises(error):
        await interactor.issue_upload(command)
    assert journal == []
