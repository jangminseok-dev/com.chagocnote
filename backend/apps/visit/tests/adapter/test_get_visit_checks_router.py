from datetime import date

from hub.app.errors import FamilyNotFoundError
from visit.adapter.inbound.api.v1.get_visit_checks_router import get_visit_checks_router
from visit.adapter.inbound.api.v1.get_visit_router import get_visit_router
from visit.app.dtos.check_view_dto import CheckView
from visit.app.dtos.get_visit_checks_dto import PetChecksView, VisitChecksView
from visit.dependencies.get_visit_checks_provider import get_get_visit_checks_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

VIEW = VisitChecksView(
    customer=[CheckView("caution", "customer", {"reason": "입질", "until": date(2027, 1, 1)})],
    pets=[PetChecksView(pet_id=101, checks=[
        CheckView("consent", "pet", {"reasons": ["senior"], "state": "expired", "received_on": date(2025, 3, 1)}),
        CheckView("long_absence", "pet", {"days": 200, "last_visit_on": date(2026, 4, 28)}),
    ])],
)


def _app(stub, access=STAFF):
    return build_app(get_visit_checks_router, get_get_visit_checks_use_case, stub, access)


async def test_직원도_미리_보고_날짜는_글자로_나간다():
    stub = Recorder(VIEW)
    async with client(_app(stub)) as c:
        response = await c.get("/v1/shops/3/visit-checks?customer_id=7&pet_ids=101&pet_ids=102&date=2026-11-20")
    assert response.status_code == 200
    body = response.json()
    assert body["customer"] == [{"code": "caution", "scope": "customer",
                                 "detail": {"reason": "입질", "until": "2027-01-01"}}]
    assert body["pets"][0]["pet_id"] == 101
    assert body["pets"][0]["checks"][0]["detail"] == {
        "reasons": ["senior"], "state": "expired", "received_on": "2025-03-01"}
    assert body["pets"][0]["checks"][1]["detail"] == {"days": 200, "last_visit_on": "2026-04-28"}
    query = stub.calls[0]
    assert (query.customer_id, query.pet_ids, query.day, query.ctx.shop_id) == (7, (101, 102), date(2026, 11, 20), 3)


async def test_아이를_주지_않으면_빈_묶음으로_넘긴다():
    stub = Recorder(VIEW)
    async with client(_app(stub)) as c:
        await c.get("/v1/shops/3/visit-checks?customer_id=7&date=2026-11-20")
    assert stub.calls[0].pet_ids == ()


async def test_빠지거나_깨진_질의는_422_다():
    stub = Recorder(VIEW)
    async with client(_app(stub)) as c:
        for query in (
            "date=2026-11-20",                                   # 고객 없음
            "customer_id=7",                                     # 날짜 없음
            "customer_id=0&date=2026-11-20",
            "customer_id=7&date=내일",
            "customer_id=7&date=2026-02-31",
            "customer_id=7&date=2026-11-20&pet_ids=abc",
            "customer_id=7&date=2026-11-20&pet_ids=0",
            "customer_id=7&date=2026-11-20&" + "&".join(f"pet_ids={i}" for i in range(1, 12)),   # 11마리
            "customer_id=99999999999999999999&date=2026-11-20",
        ):
            assert error_of(await c.get(f"/v1/shops/3/visit-checks?{query}")) == (422, "VALIDATION_ERROR"), query
    assert stub.calls == []


async def test_없는_고객은_404_CUSTOMER_NOT_FOUND_다():
    stub = Recorder(error=FamilyNotFoundError("고객을 찾을 수 없습니다."))
    async with client(_app(stub)) as c:
        response = await c.get("/v1/shops/3/visit-checks?customer_id=7&date=2026-11-20")
    assert error_of(response) == (404, "CUSTOMER_NOT_FOUND")


def test_방문_상세보다_먼저_붙지_않아도_경로가_겹치지_않는다():
    # /visit-checks 는 /visits/{visit_id} 와 접두가 다르다 — 등록 순서와 상관없다.
    paths = {r.path for r in get_visit_checks_router.routes} | {r.path for r in get_visit_router.routes}
    assert "/v1/shops/{shop_id}/visit-checks" in paths
