from datetime import datetime, timezone

from media.adapter.inbound.api.v1.issue_upload_router import issue_upload_router
from media.app.dtos.issue_upload_dto import IssuedUploadView, UploadTargetsView
from media.dependencies.issue_upload_provider import get_issue_upload_use_case
from media.domain.errors import MediaTooLargeError
from media.tests.helpers.api import NO_RECORD, Recorder, build_app, client, error_of

ISSUED = IssuedUploadView(
    media_id=7, puts=UploadTargetsView(original="put://o", display=None, thumb="put://t"),
    expires_at=datetime(2026, 9, 24, 3, 15, tzinfo=timezone.utc),
)
BODY = {"kind": "video", "content_type": "video/mp4", "byte_size": 150_000_000, "width": 1920, "height": 1080,
        "duration_seconds": 42}


async def test_직원은_발급받는다_201():
    stub = Recorder(ISSUED)
    async with client(build_app(issue_upload_router, get_issue_upload_use_case, stub)) as c:
        response = await c.post("/v1/shops/3/media/uploads", json=BODY)
    assert (response.status_code, response.json()) == (201, {
        "media_id": 7, "puts": {"original": "put://o", "display": None, "thumb": "put://t"},
        "expires_at": "2026-09-24T03:15:00Z"})
    call = stub.calls[0]
    assert (call.ctx.shop_id, call.kind, call.byte_size, call.duration_seconds) == (3, "video", 150_000_000, 42)


async def test_기록_권한이_없으면_403():
    async with client(build_app(issue_upload_router, get_issue_upload_use_case, Recorder(ISSUED), NO_RECORD)) as c:
        response = await c.post("/v1/shops/3/media/uploads", json=BODY)
    assert error_of(response) == (403, "PERMISSION_DENIED")


async def test_칸의_범위를_넘으면_422_다():
    async with client(build_app(issue_upload_router, get_issue_upload_use_case, Recorder(ISSUED))) as c:
        for bad in ({**BODY, "kind": "audio"}, {**BODY, "width": 40_000}, {**BODY, "byte_size": "150"},
                    {**BODY, "byte_size": 0}, {k: v for k, v in BODY.items() if k != "height"}):
            assert error_of(await c.post("/v1/shops/3/media/uploads", json=bad)) == (422, "VALIDATION_ERROR")


async def test_도메인_거절은_코드로_나간다():
    stub = Recorder(error=MediaTooLargeError("큼"))
    async with client(build_app(issue_upload_router, get_issue_upload_use_case, stub)) as c:
        response = await c.post("/v1/shops/3/media/uploads", json=BODY)
    assert error_of(response) == (422, "MEDIA_TOO_LARGE")
