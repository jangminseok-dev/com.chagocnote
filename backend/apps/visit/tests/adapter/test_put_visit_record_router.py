from decimal import Decimal

from visit.adapter.inbound.api.v1.put_visit_record_router import put_visit_record_router
from visit.app.dtos.record_view_dto import RecordItemView, RecordMediaView, RecordView
from visit.dependencies.put_visit_record_provider import get_put_visit_record_use_case
from visit.domain.errors import (
    RecordItemDuplicateError,
    RecordSalesForbiddenError,
    RecordVersionConflictError,
    VisitNoRecordYetError,
)
from visit.tests.helpers.api import READ_ONLY, STAFF, Recorder, build_app, client, error_of

VIEW = RecordView(
    visit_id=4, weight_kg=Decimal("3.4"), care_note="케어", internal_note=None, payment_method="card",
    total_amount=28_000, items=[RecordItemView(menu_id=1, name="목욕", amount=28_000)],
    media=[RecordMediaView(media_id=51, kind="photo", phase="after", sort_order=0, original_url="o", display_url="d",
                           thumb_url="t", width=3000, height=2000, duration_seconds=None)],
    version=2,
)
BODY = {"version": 1, "weight_kg": 3.4, "care_note": " 케어 ", "payment_method": "card", "total_amount": 28000,
        "items": [{"menu_id": 1, "amount": 28000}], "media": [{"media_id": 51, "phase": "after", "sort_order": 0}]}


async def test_직원은_기록을_쓰고_기록_전체를_받는다():
    stub = Recorder(VIEW)
    async with client(build_app(put_visit_record_router, get_put_visit_record_use_case, stub, STAFF)) as c:
        response = await c.put("/v1/shops/3/visits/4/record", json=BODY)
    assert (response.status_code, response.json()["version"], response.json()["weight_kg"]) == (200, 2, 3.4)
    call = stub.calls[0]
    assert (call.visit_id, call.version, call.record.weight_kg, call.record.care_note) == (4, 1, Decimal("3.4"), "케어")
    assert (call.record.items[0].amount, call.record.media[0].phase) == (28000, "after")


async def test_빈_몸통은_모든_칸을_비운_첫_기록이다():
    stub = Recorder(VIEW)
    async with client(build_app(put_visit_record_router, get_put_visit_record_use_case, stub)) as c:
        await c.put("/v1/shops/3/visits/4/record", json={})
    wanted = stub.calls[0].record
    assert (stub.calls[0].version, wanted.items, wanted.media, wanted.has_money) == (None, (), (), False)


async def test_기록_권한이_없으면_403():
    async with client(build_app(put_visit_record_router, get_put_visit_record_use_case, Recorder(VIEW), READ_ONLY)) as c:
        assert error_of(await c.put("/v1/shops/3/visits/4/record", json=BODY)) == (403, "PERMISSION_DENIED")


async def test_입력_경계를_넘으면_422_다():
    placement = {"media_id": 51, "phase": "after", "sort_order": 0}
    bad_bodies = [
        {"weight_kg": 0}, {"weight_kg": 1000}, {"weight_kg": 3.25}, {"total_amount": -1},
        {"total_amount": 100_000_001}, {"items": [{"menu_id": 1, "amount": 100_000_001}]},
        {"payment_method": "point"}, {"care_note": "가" * 1001}, {"internal_note": "a\x00b"},
        {"media": [placement, placement]},
        {"media": [placement, {**placement, "media_id": 52}]},              # 같은 자리
        {"media": [{**placement, "sort_order": 100}]}, {"media": [{**placement, "phase": "during"}]},
        {"media": [{**placement, "media_id": 60 + i, "sort_order": i} for i in range(34)]},
        {"version": 0}, {"version": "1"},
    ]
    async with client(build_app(put_visit_record_router, get_put_visit_record_use_case, Recorder(VIEW))) as c:
        for body in bad_bodies:
            assert error_of(await c.put("/v1/shops/3/visits/4/record", json=body)) == (422, "VALIDATION_ERROR"), body


async def test_도메인_거절은_코드로_나간다():
    cases = [(VisitNoRecordYetError("아직"), (409, "VISIT_NO_RECORD_YET")),
             (RecordVersionConflictError("버전"), (409, "RECORD_VERSION_CONFLICT")),
             (RecordItemDuplicateError("중복"), (422, "RECORD_ITEM_DUPLICATE")),
             (RecordSalesForbiddenError("돈"), (403, "PERMISSION_DENIED"))]
    for error, expected in cases:
        async with client(build_app(put_visit_record_router, get_put_visit_record_use_case, Recorder(error=error))) as c:
            assert error_of(await c.put("/v1/shops/3/visits/4/record", json=BODY)) == expected
