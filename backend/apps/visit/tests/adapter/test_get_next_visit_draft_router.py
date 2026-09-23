from datetime import datetime
from zoneinfo import ZoneInfo

from visit.adapter.inbound.api.v1.get_next_visit_draft_router import get_next_visit_draft_router
from visit.app.dtos.get_next_visit_draft_dto import NextVisitDraftView
from visit.dependencies.get_next_visit_draft_provider import get_get_next_visit_draft_use_case
from visit.domain.errors import VisitStateConflictError
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

DRAFT = NextVisitDraftView(customer_id=1, pet_ids=[101, 102],
                           starts_at=datetime(2026, 10, 21, 14, tzinfo=ZoneInfo("Asia/Seoul")),
                           duration_minutes=150, menus=[], interval_weeks=4)


async def test_다음_예약_초안을_준다():
    stub = Recorder(DRAFT)
    async with client(build_app(get_next_visit_draft_router, get_get_next_visit_draft_use_case, stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/visits/9/next-draft")
    assert response.json() == {"customer_id": 1, "pet_ids": [101, 102], "starts_at": "2026-10-21T14:00:00+09:00",
                               "duration_minutes": 150, "menus": [], "interval_weeks": 4}
    assert stub.calls[0].visit_id == 9


async def test_취소_노쇼한_방문이면_409():
    stub = Recorder(error=VisitStateConflictError("취소함"))
    async with client(build_app(get_next_visit_draft_router, get_get_next_visit_draft_use_case, stub)) as c:
        assert error_of(await c.get("/v1/shops/3/visits/9/next-draft")) == (409, "VISIT_STATE_CONFLICT")
