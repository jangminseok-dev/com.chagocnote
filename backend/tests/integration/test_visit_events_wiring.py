"""visit 이 발행한 이벤트가 실제 배선(main.py 의 버스 꽂기, 요청의 세션)으로 구독자에 닿는지 확인한다.

구독자가 던지면 요청은 500 이고 방문 저장도 롤백된다(설계 5.1, N13).
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from core.observer.in_process_event_bus import subscribe, unsubscribe
from hub.app.dtos.visit_events import VisitCanceled, VisitRescheduled, VisitReserved
from tests.integration.support import bearer, make_operator, shop_with_owner

pytestmark = pytest.mark.integration

SEOUL = ZoneInfo("Asia/Seoul")
CUSTOMER = {"name": "김민지", "phone": "010-1234-5678", "marketing_consent": True}
PET = {"name": "콩이", "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True, "birth_year": 2021,
       "weight_kg": 3.2, "no_known_conditions": True}


def _at(days: int, hour: int) -> str:
    day = datetime.now(SEOUL).date() + timedelta(days=days)
    return datetime(day.year, day.month, day.day, hour, tzinfo=SEOUL).isoformat()


@pytest.fixture
def received():
    """구독자 하나를 실제 버스에 등록해 받은 (세션, 이벤트)를 모은다. 끝나면 자기 구독자만 뺀다(실제 구독자는 남긴다)."""
    events = []

    async def collect(session, event):
        await session.execute(text("SELECT 1"))   # 요청의 세션이 그대로 넘어온다
        events.append(event)

    subscribe(collect)
    yield events
    unsubscribe(collect)


async def _shop(wired):
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    headers = bearer(owner["access_token"])
    response = await wired.api.post(
        f"/v1/shops/{shop_id}/customers", json={"customer": CUSTOMER, "pet": PET}, headers=headers)
    assert response.status_code == 201, response.text
    body = response.json()
    return shop_id, headers, body["customer"]["customer_id"], body["pets"][0]["pet_id"]


def _booking(customer_id, pet_id, starts_at):
    return {"customer_id": customer_id, "pet_ids": [pet_id], "starts_at": starts_at}


async def test_등록_수정_취소가_순서대로_이벤트로_닿는다(wired, received):
    shop_id, headers, customer_id, pet_id = await _shop(wired)
    booked = await wired.api.post(f"/v1/shops/{shop_id}/visits", json=_booking(customer_id, pet_id, _at(3, 14)),
                                  headers=headers)
    assert booked.status_code == 201, booked.text
    visit = booked.json()["visits"][0]
    visit_id = visit["visit_id"]
    moved = await wired.api.put(
        f"/v1/shops/{shop_id}/visits/{visit_id}",
        json={"starts_at": _at(3, 16), "pet_id": pet_id, "duration_minutes": visit["duration_minutes"],
              "menu_ids": [], "memo": None},
        headers=headers,
    )
    assert moved.status_code == 200, moved.text
    canceled = await wired.api.post(
        f"/v1/shops/{shop_id}/visits/transitions",
        json={"visit_ids": [visit_id], "action": "cancel", "cancel_reason": "shop_reason"}, headers=headers)
    assert canceled.status_code == 200, canceled.text

    assert [type(e) for e in received] == [VisitReserved, VisitRescheduled, VisitCanceled]
    assert {(e.ctx.shop_id, e.visit_id, e.customer_id, e.pet_id) for e in received} == {
        (shop_id, visit_id, customer_id, pet_id)}
    assert received[1].previous_starts_at == received[0].starts_at
    assert received[1].starts_at == received[2].starts_at == datetime.fromisoformat(_at(3, 16))
    assert received[2].reason == "shop_reason"


async def test_구독자가_던지면_500_이고_방문은_생기지_않는다(wired):
    """N13 — 구독자는 발행한 요청과 같은 트랜잭션이다. 실패하면 방문 저장도 롤백된다."""
    import main

    async def explode(session, event):
        raise RuntimeError("구독자 실패")

    subscribe(explode)
    try:
        shop_id, headers, customer_id, pet_id = await _shop(wired)
        async with AsyncClient(transport=ASGITransport(app=main.app, raise_app_exceptions=False),
                               base_url="http://api") as api:
            booked = await api.post(f"/v1/shops/{shop_id}/visits", json=_booking(customer_id, pet_id, _at(3, 14)),
                                    headers=headers)
        assert booked.status_code == 500
    finally:
        unsubscribe(explode)
    day = (datetime.now(SEOUL).date() + timedelta(days=3)).isoformat()
    listed = await wired.api.get(f"/v1/shops/{shop_id}/visits?date={day}", headers=headers)
    assert listed.status_code == 200 and listed.json()["items"] == []
