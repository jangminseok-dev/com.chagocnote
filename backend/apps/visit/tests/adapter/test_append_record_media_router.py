from visit.adapter.inbound.api.v1.append_record_media_router import append_record_media_router
from visit.app.dtos.record_view_dto import RecordView
from visit.dependencies.append_record_media_provider import get_append_record_media_use_case
from visit.tests.helpers.api import READ_ONLY, STAFF, Recorder, build_app, client, error_of

VIEW = RecordView(visit_id=4, weight_kg=None, care_note=None, internal_note=None, payment_method=None,
                  total_amount=None, items=[], media=[], version=1)


async def test_직원은_사진을_덧붙인다():
    stub = Recorder(VIEW)
    async with client(build_app(append_record_media_router, get_append_record_media_use_case, stub, STAFF)) as c:
        response = await c.post("/v1/shops/3/visits/4/record/media", json={"media_id": 51, "phase": "before"})
    assert (response.status_code, response.json()["version"]) == (200, 1)
    assert (stub.calls[0].visit_id, stub.calls[0].media_id, stub.calls[0].phase) == (4, 51, "before")


async def test_권한이_없거나_몸통이_틀리면_거절한다():
    async with client(build_app(append_record_media_router, get_append_record_media_use_case, Recorder(VIEW),
                                READ_ONLY)) as c:
        assert error_of(await c.post("/v1/shops/3/visits/4/record/media", json={"media_id": 51, "phase": "after"})) == (
            403, "PERMISSION_DENIED")
    async with client(build_app(append_record_media_router, get_append_record_media_use_case, Recorder(VIEW))) as c:
        for body in ({"media_id": 51}, {"media_id": 0, "phase": "after"}, {"media_id": 51, "phase": "during"}):
            assert error_of(await c.post("/v1/shops/3/visits/4/record/media", json=body)) == (422, "VALIDATION_ERROR")
