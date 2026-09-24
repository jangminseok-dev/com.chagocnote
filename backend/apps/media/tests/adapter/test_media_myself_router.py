from media.adapter.inbound.api.v1.media_myself_router import media_myself_router
from media.app.dtos.media_myself_dto import MediaMyselfResponse
from media.dependencies.media_myself_provider import get_media_myself_use_case
from media.tests.helpers.api import NO_RECORD, Recorder, build_app, client


async def test_멤버는_자기소개를_본다():
    stub = Recorder(MediaMyselfResponse(id=6, name="미디어 (media)", introduction="소개"))
    async with client(build_app(media_myself_router, get_media_myself_use_case, stub, NO_RECORD)) as c:
        response = await c.get("/v1/shops/3/media/myself")
    assert response.json() == {"id": 6, "name": "미디어 (media)", "introduction": "소개"}
