from visit.adapter.inbound.api.v1.preview_repeat_router import preview_repeat_router
from visit.app.dtos.preview_repeat_dto import OccurrenceView, RepeatPreviewView
from visit.dependencies.preview_repeat_provider import get_preview_repeat_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client
from visit.tests.helpers.builders import kst

BASE = "/v1/shops/3/visits/repeat-preview?customer_id=7&starts_at=2026-11-20T14:00:00%2B09:00"


def _app(stub):
    return build_app(preview_repeat_router, get_preview_repeat_use_case, stub, STAFF)


async def test_repeat_preview_는_pet_ids_를_반복_쿼리로_받는다():
    view = RepeatPreviewView(interval_weeks=4, count=2, beyond_horizon=0, occurrences=[
        OccurrenceView(index=1, starts_at=kst(11, 20, 14), warnings=[], taken=False),
        OccurrenceView(index=2, starts_at=kst(12, 18, 14), warnings=["closed_day"], taken=True)])
    stub = Recorder(view)
    async with client(_app(stub)) as c:
        response = await c.get(f"{BASE}&pet_ids=101&pet_ids=102&menu_ids=5&interval_weeks=4&count=2")
    assert response.status_code == 200
    body = response.json()
    assert body["occurrences"][1] == {"index": 2, "starts_at": "2026-12-18T05:00:00Z", "warnings": ["closed_day"],
                                      "taken": True}
    assert (body["interval_weeks"], body["count"], body["beyond_horizon"]) == (4, 2, 0)
    query = stub.calls[0]
    assert (query.pet_ids, query.menu_ids, query.interval_weeks, query.count, query.duration_minutes) == (
        (101, 102), (5,), 4, 2, None)
    assert query.starts_at == kst(11, 20, 14)


async def test_repeat_preview_의_간격_13_횟수_1_은_422():
    async with client(_app(Recorder())) as c:
        for extra in ("&interval_weeks=13&count=6", "&interval_weeks=0&count=6", "&interval_weeks=4&count=1",
                      "&interval_weeks=4&count=13", "&interval_weeks=4"):
            assert (await c.get(BASE + extra)).status_code == 422, extra
        naive = "/v1/shops/3/visits/repeat-preview?customer_id=7&starts_at=2026-11-20T14:00:00&interval_weeks=4&count=2"
        assert (await c.get(naive)).status_code == 422   # 시간대가 없는 시각
