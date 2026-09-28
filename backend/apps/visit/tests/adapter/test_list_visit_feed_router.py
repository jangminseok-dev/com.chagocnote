from datetime import datetime
from zoneinfo import ZoneInfo

from visit.adapter.inbound.api.v1.list_visit_feed_router import list_visit_feed_router
from visit.app.dtos.list_visit_feed_dto import FeedItemView, VisitFeedView
from visit.dependencies.list_visit_feed_provider import get_list_visit_feed_use_case
from visit.domain.errors import VisitInputError
from visit.tests.helpers.api import READ_ONLY, Recorder, build_app, client, error_of
from visit.tests.helpers.views import visit_view

_V = visit_view()
FEED = VisitFeedView(
    items=[FeedItemView(visit_id=4, customer=_V.customer, pet=_V.pet,
                        completed_at=datetime(2026, 9, 9, 12, tzinfo=ZoneInfo("Asia/Seoul")), cover="t/51",
                        menus=["전체 미용"], care_note="눈물 자국", media_count=3, report_sent=True)],
    next_cursor="abc",
)


async def test_멤버는_피드를_본다_기본은_20개():
    stub = Recorder(FEED)
    async with client(build_app(list_visit_feed_router, get_list_visit_feed_use_case, stub, READ_ONLY)) as c:
        response = await c.get("/v1/shops/3/visits/feed")
        await c.get("/v1/shops/3/visits/feed?cursor=abc&limit=50&pet_id=101")
    body = response.json()
    assert (body["next_cursor"], body["items"][0]["cover"], body["items"][0]["pet"]["name"]) == ("abc", "t/51", "콩이")
    assert body["items"][0]["completed_at"] == "2026-09-09T12:00:00+09:00"
    assert body["items"][0]["report_sent"] is True
    assert [(q.cursor, q.limit, q.pet_id) for q in stub.calls] == [(None, 20, None), ("abc", 50, 101)]


async def test_쪽_크기와_반려동물_ID_의_범위_잘못된_커서():
    async with client(build_app(list_visit_feed_router, get_list_visit_feed_use_case, Recorder(FEED))) as c:
        for query in ("limit=0", "limit=51", "pet_id=0", "cursor=" + "a" * 201):
            assert error_of(await c.get(f"/v1/shops/3/visits/feed?{query}")) == (422, "VALIDATION_ERROR")
    stub = Recorder(error=VisitInputError("목록 위치(cursor)가 올바르지 않습니다."))
    async with client(build_app(list_visit_feed_router, get_list_visit_feed_use_case, stub)) as c:
        assert error_of(await c.get("/v1/shops/3/visits/feed?cursor=zz")) == (422, "VALIDATION_ERROR")
