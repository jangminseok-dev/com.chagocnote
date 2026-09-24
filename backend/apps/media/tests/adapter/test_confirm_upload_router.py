from media.adapter.inbound.api.v1.confirm_upload_router import confirm_upload_router
from media.app.dtos.media_view_dto import MediaView
from media.dependencies.confirm_upload_provider import get_confirm_upload_use_case
from media.domain.errors import MediaNotFoundError, MediaNotUploadedError
from media.tests.helpers.api import NO_RECORD, Recorder, build_app, client, error_of

READY = MediaView(media_id=7, kind="photo", status="ready", size_bytes=3_000_000, width=3000, height=2000,
                  duration_seconds=None)


async def test_확인하면_ready_객체를_준다():
    stub = Recorder(READY)
    async with client(build_app(confirm_upload_router, get_confirm_upload_use_case, stub)) as c:
        response = await c.post("/v1/shops/3/media/7/confirm")
    assert (response.status_code, response.json()["status"], response.json()["size_bytes"]) == (200, "ready", 3_000_000)
    assert (stub.calls[0].ctx.shop_id, stub.calls[0].media_id) == (3, 7)


async def test_오류는_코드로_나간다():
    for error, expected in ((MediaNotUploadedError("아직"), (409, "MEDIA_NOT_UPLOADED")),
                            (MediaNotFoundError("없음"), (404, "MEDIA_NOT_FOUND"))):
        async with client(build_app(confirm_upload_router, get_confirm_upload_use_case, Recorder(error=error))) as c:
            assert error_of(await c.post("/v1/shops/3/media/7/confirm")) == expected


async def test_기록_권한이_없거나_ID_가_bigint_를_넘으면_거절한다():
    async with client(build_app(confirm_upload_router, get_confirm_upload_use_case, Recorder(READY), NO_RECORD)) as c:
        assert error_of(await c.post("/v1/shops/3/media/7/confirm")) == (403, "PERMISSION_DENIED")
    async with client(build_app(confirm_upload_router, get_confirm_upload_use_case, Recorder(READY))) as c:
        assert error_of(await c.post(f"/v1/shops/3/media/{2**63}/confirm")) == (422, "VALIDATION_ERROR")
